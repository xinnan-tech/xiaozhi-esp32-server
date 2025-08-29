package xiaozhi.migration;

import java.io.File;
import java.nio.file.Files;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.util.*;

import com.google.gson.*;

/**
 * Standalone Content Library Migration
 * Can be run independently to populate the content_library table
 */
public class StandaloneContentMigration {
    
    // Database configuration - adjust these for your environment
    private static final String DB_URL = "jdbc:mysql://localhost:3306/xiaozhi_esp32?useSSL=false&serverTimezone=UTC&allowPublicKeyRetrieval=true";
    private static final String DB_USER = "root";
    private static final String DB_PASSWORD = "123456";
    
    // Content paths
    private static final String BASE_PATH = "/Users/craftech360/Downloads/app/cheeko_server/main/xiaozhi-server";
    private static final String MUSIC_PATH = BASE_PATH + "/music";
    private static final String STORIES_PATH = BASE_PATH + "/stories";
    
    private static final Gson gson = new GsonBuilder().setPrettyPrinting().create();
    private static Connection connection;
    
    public static void main(String[] args) {
        System.out.println("==========================================");
        System.out.println("Content Library Standalone Migration");
        System.out.println("==========================================\n");
        
        try {
            // Connect to database
            connectToDatabase();
            
            // Clear existing data (optional - comment out if you want to keep existing data)
            clearExistingData();
            
            // Migrate music
            migrateMusicContent();
            
            // Migrate stories
            migrateStoryContent();
            
            // Print summary
            printSummary();
            
            System.out.println("\nMigration completed successfully!");
            
        } catch (Exception e) {
            System.err.println("Migration failed: " + e.getMessage());
            e.printStackTrace();
        } finally {
            closeConnection();
        }
    }
    
    private static void connectToDatabase() throws Exception {
        System.out.println("Connecting to database...");
        Class.forName("com.mysql.cj.jdbc.Driver");
        connection = DriverManager.getConnection(DB_URL, DB_USER, DB_PASSWORD);
        connection.setAutoCommit(false);
        System.out.println("Connected to database successfully\n");
    }
    
    private static void clearExistingData() throws Exception {
        System.out.println("Clearing existing data...");
        PreparedStatement stmt = connection.prepareStatement("DELETE FROM content_library");
        int deleted = stmt.executeUpdate();
        connection.commit();
        System.out.println("Deleted " + deleted + " existing records\n");
    }
    
    private static void migrateMusicContent() throws Exception {
        System.out.println("Migrating music content...");
        
        File musicDir = new File(MUSIC_PATH);
        File[] languageDirs = musicDir.listFiles(File::isDirectory);
        
        if (languageDirs == null) {
            System.out.println("No music directories found");
            return;
        }
        
        int totalMusic = 0;
        for (File langDir : languageDirs) {
            String language = langDir.getName();
            System.out.println("  Processing language: " + language);
            
            File metadataFile = new File(langDir, "metadata.json");
            if (!metadataFile.exists()) {
                System.out.println("    No metadata.json found");
                continue;
            }
            
            String jsonContent = Files.readString(metadataFile.toPath());
            JsonObject jsonObject = JsonParser.parseString(jsonContent).getAsJsonObject();
            
            int count = 0;
            for (Map.Entry<String, JsonElement> entry : jsonObject.entrySet()) {
                String title = entry.getKey();
                JsonObject info = entry.getValue().getAsJsonObject();
                
                if (insertContentItem(title, info, "music", language)) {
                    count++;
                }
            }
            
            System.out.println("    Inserted " + count + " items");
            totalMusic += count;
        }
        
        connection.commit();
        System.out.println("Total music items migrated: " + totalMusic + "\n");
    }
    
    private static void migrateStoryContent() throws Exception {
        System.out.println("Migrating story content...");
        
        File storiesDir = new File(STORIES_PATH);
        File[] genreDirs = storiesDir.listFiles(File::isDirectory);
        
        if (genreDirs == null) {
            System.out.println("No story directories found");
            return;
        }
        
        int totalStories = 0;
        for (File genreDir : genreDirs) {
            String genre = genreDir.getName();
            System.out.println("  Processing genre: " + genre);
            
            File metadataFile = new File(genreDir, "metadata.json");
            if (!metadataFile.exists()) {
                System.out.println("    No metadata.json found");
                continue;
            }
            
            String jsonContent = Files.readString(metadataFile.toPath());
            JsonObject jsonObject = JsonParser.parseString(jsonContent).getAsJsonObject();
            
            int count = 0;
            for (Map.Entry<String, JsonElement> entry : jsonObject.entrySet()) {
                String title = entry.getKey();
                JsonObject info = entry.getValue().getAsJsonObject();
                
                if (insertContentItem(title, info, "story", genre)) {
                    count++;
                }
            }
            
            System.out.println("    Inserted " + count + " items");
            totalStories += count;
        }
        
        connection.commit();
        System.out.println("Total story items migrated: " + totalStories + "\n");
    }
    
    private static boolean insertContentItem(String title, JsonObject info, String contentType, String category) {
        try {
            String sql = "INSERT INTO content_library (id, title, romanized, filename, content_type, " +
                        "category, alternatives, aws_s3_url, duration_seconds, file_size_bytes, is_active) " +
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";
            
            PreparedStatement stmt = connection.prepareStatement(sql);
            
            // Generate UUID
            String id = UUID.randomUUID().toString();
            
            // Get values from JSON
            String romanized = getJsonString(info, "romanized");
            String filename = getJsonString(info, "filename");
            
            // Build alternatives JSON array
            JsonArray alternativesArray = info.getAsJsonArray("alternatives");
            String alternativesJson = null;
            if (alternativesArray != null) {
                alternativesJson = gson.toJson(alternativesArray);
            }
            
            // Set parameters
            stmt.setString(1, id);
            stmt.setString(2, title);
            stmt.setString(3, romanized);
            stmt.setString(4, filename);
            stmt.setString(5, contentType);
            stmt.setString(6, category);
            stmt.setString(7, alternativesJson);
            stmt.setString(8, getJsonString(info, "aws_s3_url")); // May be null
            stmt.setObject(9, getJsonInteger(info, "duration_seconds")); // May be null
            stmt.setObject(10, getJsonLong(info, "file_size_bytes")); // May be null
            stmt.setInt(11, 1); // is_active
            
            stmt.executeUpdate();
            return true;
            
        } catch (Exception e) {
            System.err.println("    Failed to insert '" + title + "': " + e.getMessage());
            return false;
        }
    }
    
    private static String getJsonString(JsonObject obj, String key) {
        JsonElement element = obj.get(key);
        return (element != null && !element.isJsonNull()) ? element.getAsString() : null;
    }
    
    private static Integer getJsonInteger(JsonObject obj, String key) {
        JsonElement element = obj.get(key);
        return (element != null && !element.isJsonNull()) ? element.getAsInt() : null;
    }
    
    private static Long getJsonLong(JsonObject obj, String key) {
        JsonElement element = obj.get(key);
        return (element != null && !element.isJsonNull()) ? element.getAsLong() : null;
    }
    
    private static void printSummary() throws Exception {
        System.out.println("==========================================");
        System.out.println("Migration Summary");
        System.out.println("==========================================");
        
        // Count records by type
        PreparedStatement stmt = connection.prepareStatement(
            "SELECT content_type, COUNT(*) as count FROM content_library GROUP BY content_type"
        );
        ResultSet rs = stmt.executeQuery();
        
        while (rs.next()) {
            String type = rs.getString("content_type");
            int count = rs.getInt("count");
            System.out.println(type.toUpperCase() + ": " + count + " items");
        }
        
        // Count by category
        System.out.println("\nBy Category:");
        stmt = connection.prepareStatement(
            "SELECT content_type, category, COUNT(*) as count FROM content_library " +
            "GROUP BY content_type, category ORDER BY content_type, category"
        );
        rs = stmt.executeQuery();
        
        String lastType = "";
        while (rs.next()) {
            String type = rs.getString("content_type");
            String category = rs.getString("category");
            int count = rs.getInt("count");
            
            if (!type.equals(lastType)) {
                System.out.println("\n" + type.toUpperCase() + ":");
                lastType = type;
            }
            System.out.println("  - " + category + ": " + count);
        }
    }
    
    private static void closeConnection() {
        try {
            if (connection != null && !connection.isClosed()) {
                connection.close();
                System.out.println("\nDatabase connection closed");
            }
        } catch (Exception e) {
            System.err.println("Error closing connection: " + e.getMessage());
        }
    }
}
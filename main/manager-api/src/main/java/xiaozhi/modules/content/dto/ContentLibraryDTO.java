package xiaozhi.modules.content.dto;

import java.io.Serializable;
import java.util.List;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

/**
 * Content Library Data Transfer Object
 * Used for API requests and responses
 */
@Data
@Schema(description = "Content Library Data Transfer Object")
public class ContentLibraryDTO implements Serializable {
    private static final long serialVersionUID = 1L;

    @Schema(description = "Content unique identifier", example = "content_123")
    private String id;

    @Schema(description = "Content title", example = "Baby Shark Dance")
    private String title;

    @Schema(description = "Romanized version of the title", example = "Baby Shark Dance")
    private String romanized;

    @Schema(description = "Original filename", example = "Baby Shark Dance.mp3")
    private String filename;

    @Schema(description = "Content type", example = "music", allowableValues = {"music", "story"})
    private String contentType;

    @Schema(description = "Category (Language for music, Genre for stories)", example = "English")
    private String category;

    @Schema(description = "Alternative search terms")
    private List<String> alternatives;

    @Schema(description = "AWS S3 URL for the audio file")
    private String awsS3Url;

    @Schema(description = "Duration in seconds", example = "154")
    private Integer durationSeconds;

    @Schema(description = "File size in bytes", example = "2048000")
    private Long fileSizeBytes;

    @Schema(description = "Active status", example = "true")
    private Boolean isActive;

    @Schema(description = "Formatted duration (MM:SS)", example = "2:34")
    private String formattedDuration;

    @Schema(description = "Human readable file size", example = "2.0 MB")
    private String formattedFileSize;

    /**
     * Get formatted duration in MM:SS format
     */
    public String getFormattedDuration() {
        if (durationSeconds == null || durationSeconds <= 0) {
            return "--:--";
        }
        int minutes = durationSeconds / 60;
        int seconds = durationSeconds % 60;
        return String.format("%d:%02d", minutes, seconds);
    }

    /**
     * Get human readable file size
     */
    public String getFormattedFileSize() {
        if (fileSizeBytes == null || fileSizeBytes <= 0) {
            return "Unknown";
        }
        
        final String[] units = {"B", "KB", "MB", "GB"};
        double size = fileSizeBytes;
        int unitIndex = 0;
        
        while (size >= 1024 && unitIndex < units.length - 1) {
            size /= 1024;
            unitIndex++;
        }
        
        if (unitIndex == 0) {
            return String.format("%.0f %s", size, units[unitIndex]);
        } else {
            return String.format("%.1f %s", size, units[unitIndex]);
        }
    }
}
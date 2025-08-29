# Content Library Migration Guide

This guide provides comprehensive instructions for migrating content metadata from JSON files in the xiaozhi-server directory structure to the `content_library` database table.

## Overview

The migration script processes JSON metadata files containing information about music and story content, parsing them and inserting the data into the database using the ContentLibraryService.batchInsertContent() method.

### Directory Structure

The migration expects the following directory structure:

```
xiaozhi-server/
├── music/
│   ├── English/
│   │   └── metadata.json
│   ├── Hindi/
│   │   └── metadata.json
│   ├── Kannada/
│   │   └── metadata.json
│   ├── Phonics/
│   │   └── metadata.json
│   └── Telugu/
│       └── metadata.json
└── stories/
    ├── Adventure/
    │   └── metadata.json
    ├── Bedtime/
    │   └── metadata.json
    ├── Educational/
    │   └── metadata.json
    ├── Fairy Tales/
    │   └── metadata.json
    └── Fantasy/
        └── metadata.json
```

### JSON Metadata Format

Each `metadata.json` file contains content items in the following format:

```json
{
  "Content Title": {
    "romanized": "Content Title",
    "filename": "Content Title.mp3",
    "alternatives": [
      "alternative search term 1",
      "alternative search term 2",
      "..."
    ],
    "aws_s3_url": "https://s3.amazonaws.com/...",
    "duration_seconds": 154,
    "file_size_bytes": 2048000
  }
}
```

## Running the Migration

### Method 1: Using the Shell Script (Recommended)

The easiest way to run the migration is using the provided shell script:

```bash
# Make the script executable (if not already)
chmod +x run-migration.sh

# Run with default settings
./run-migration.sh

# Run with custom options
./run-migration.sh --path /path/to/xiaozhi-server --batch-size 50 --verbose

# Check prerequisites only
./run-migration.sh --check-only

# Dry run (test without database changes)
./run-migration.sh --dry-run
```

#### Shell Script Options

- `--help`: Show usage information
- `--path PATH`: Specify xiaozhi-server directory path
- `--batch-size SIZE`: Set batch size for database operations (default: 100)
- `--dry-run`: Test run without actual database changes
- `--verbose`: Enable detailed logging
- `--check-only`: Only check prerequisites

### Method 2: Using Maven

```bash
# Build the project
mvn clean package -DskipTests

# Run the migration
mvn exec:java -Dexec.mainClass="xiaozhi.migration.MigrationRunner" -Dspring.profiles.active=migration
```

### Method 3: Using JAR File

```bash
# Build the JAR
mvn clean package -DskipTests

# Run the migration
java -jar target/manager-api.jar --spring.profiles.active=migration
```

### Method 4: Using the Standalone Runner

```bash
java -cp target/manager-api.jar xiaozhi.migration.MigrationRunner --spring.profiles.active=migration
```

## Environment Variables

You can customize the migration behavior using environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `XIAOZHI_SERVER_PATH` | Path to xiaozhi-server directory | `./xiaozhi-server` |
| `MIGRATION_BATCH_SIZE` | Batch size for database operations | `100` |
| `MIGRATION_BASE_PATH` | Alternative base path | Same as XIAOZHI_SERVER_PATH |
| `JAVA_OPTS` | Additional JVM options | None |

Example:
```bash
export XIAOZHI_SERVER_PATH="/opt/xiaozhi/xiaozhi-server"
export MIGRATION_BATCH_SIZE="50"
./run-migration.sh
```

## Configuration

### Database Configuration

The migration uses the same database configuration as the main application. Ensure your `application.yml` or `application-migration.yml` contains proper database connection settings.

### Migration-Specific Configuration

The `application-migration.yml` file contains migration-specific settings:

```yaml
migration:
  content-library:
    base-path: "${user.dir}/xiaozhi-server"
    batch-size: 100
    skip-if-exists: false
    music:
      supported-languages:
        - English
        - Hindi
        - Kannada
        - Phonics
        - Telugu
    stories:
      supported-genres:
        - Adventure
        - Bedtime
        - Educational
        - "Fairy Tales"
        - Fantasy
```

## Migration Process

The migration script performs the following steps:

1. **Verification**: Checks that the directory structure exists and is valid
2. **Music Migration**: 
   - Scans each language directory in `music/`
   - Parses `metadata.json` files
   - Creates ContentLibraryDTO objects with `contentType="music"`
   - Maps directory names to categories (language names)
3. **Story Migration**:
   - Scans each genre directory in `stories/`
   - Parses `metadata.json` files  
   - Creates ContentLibraryDTO objects with `contentType="story"`
   - Maps directory names to categories (genre names)
4. **Batch Insert**: Inserts content in batches using `ContentLibraryService.batchInsertContent()`
5. **Statistics**: Provides detailed migration statistics and error reporting

## Data Mapping

The migration maps JSON metadata to database fields as follows:

| JSON Field | Database Field | Notes |
|------------|----------------|--------|
| Key (title) | `title` | The JSON object key becomes the title |
| `romanized` | `romanized` | Romanized version of the title |
| `filename` | `filename` | Original audio filename |
| `alternatives` | `alternatives` | Converted to JSON string for database storage |
| `aws_s3_url` | `aws_s3_url` | S3 URL for the audio file |
| `duration_seconds` | `duration_seconds` | Duration in seconds |
| `file_size_bytes` | `file_size_bytes` | File size in bytes |
| Directory name | `category` | Language for music, Genre for stories |
| Derived | `content_type` | "music" or "story" based on source directory |
| Generated | `id` | UUID generated automatically |
| Default | `is_active` | Set to 1 (active) by default |

## Error Handling

The migration script includes comprehensive error handling:

- **File System Errors**: Missing directories or files are reported with clear error messages
- **JSON Parse Errors**: Invalid JSON files are skipped with detailed error logs
- **Database Errors**: Failed batch inserts are retried and errors are logged
- **Data Validation**: Invalid or missing data is handled gracefully

## Logging

The migration provides detailed logging at multiple levels:

- **INFO**: General progress information
- **DEBUG**: Detailed processing information (with `--verbose` flag)
- **WARN**: Non-fatal issues that don't stop migration
- **ERROR**: Fatal errors that require attention

Log files are saved to:
- Console output (real-time)
- `logs/content-migration.log` (persistent log file)

## Monitoring Progress

The migration provides real-time progress updates:

```
2025-08-29 10:15:30 [INFO] Starting Content Library Migration...
2025-08-29 10:15:31 [INFO] Processing music language: English
2025-08-29 10:15:32 [INFO] Batch 1/5 completed: 20 items inserted
2025-08-29 10:15:33 [INFO] ================== MIGRATION SUMMARY ==================
2025-08-29 10:15:33 [INFO] Total items processed: 487
2025-08-29 10:15:33 [INFO] Total items inserted: 487
2025-08-29 10:15:33 [INFO] Total failed items: 0
```

## Troubleshooting

### Common Issues

1. **Directory not found**
   - Ensure xiaozhi-server directory exists and is accessible
   - Check path configuration and environment variables

2. **Database connection errors**
   - Verify database is running and accessible
   - Check database credentials in application configuration

3. **Permission errors**
   - Ensure the script has read permissions on JSON files
   - Check write permissions for log directory

4. **Memory issues with large datasets**
   - Reduce batch size using `--batch-size` option
   - Increase JVM heap size using `JAVA_OPTS` environment variable

### Debug Mode

Enable debug mode for detailed troubleshooting:

```bash
./run-migration.sh --verbose
```

Or set logging level:
```bash
export JAVA_OPTS="-Dlogging.level.xiaozhi.migration=DEBUG"
./run-migration.sh
```

## Validation

After migration, you can validate the results by:

1. **Check database**: Query the `content_library` table to verify data
2. **Review logs**: Check for any errors or warnings in the migration log
3. **API testing**: Use the Content Library API endpoints to test functionality

Example validation queries:

```sql
-- Check total counts
SELECT content_type, category, COUNT(*) as count 
FROM content_library 
GROUP BY content_type, category;

-- Check sample records
SELECT * FROM content_library LIMIT 10;

-- Check for any inactive records
SELECT COUNT(*) FROM content_library WHERE is_active = 0;
```

## Performance Considerations

- **Batch Size**: Default batch size is 100. Adjust based on your database performance
- **Memory**: The migration loads all content into memory before batch insert
- **Concurrent Access**: The migration should be run when the application is not heavily used
- **Transaction Size**: Large batches are processed in separate transactions

## Security Considerations

- The migration script only reads from JSON files and writes to the database
- No sensitive data is logged in plain text
- Database credentials should be properly secured in configuration files
- Consider running the migration in a maintenance window

## Next Steps

After successful migration:

1. **Verify Data**: Check that all content is properly migrated and accessible
2. **Update Documentation**: Update any API documentation with new content
3. **Test Functionality**: Test search and retrieval functionality with migrated data
4. **Monitor Performance**: Monitor database performance with the new content volume
5. **Backup**: Create a backup of the migrated data

## Support

For issues or questions regarding the migration:

1. Check the migration logs for detailed error information
2. Review this documentation for common troubleshooting steps
3. Verify the JSON file format matches the expected structure
4. Test with a smaller subset of data first if experiencing issues
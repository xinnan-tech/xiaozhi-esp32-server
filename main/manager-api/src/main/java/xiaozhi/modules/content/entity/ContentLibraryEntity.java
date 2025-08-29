package xiaozhi.modules.content.entity;

import java.io.Serializable;
import java.util.Date;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

import lombok.Data;

/**
 * Content Library Entity
 * Represents music and story content available for devices
 * 
 * @TableName content_library
 */
@TableName(value = "content_library")
@Data
public class ContentLibraryEntity implements Serializable {
    /**
     * Content unique identifier
     */
    @TableId(type = IdType.ASSIGN_UUID)
    private String id;

    /**
     * Content title
     */
    private String title;

    /**
     * Romanized version of the title
     */
    private String romanized;

    /**
     * Original filename
     */
    private String filename;

    /**
     * Content type: music or story
     */
    private String contentType;

    /**
     * Category: Language for music, Genre for stories
     */
    private String category;

    /**
     * Alternative search terms (JSON string)
     */
    private String alternatives;

    /**
     * AWS S3 URL for the audio file
     */
    private String awsS3Url;

    /**
     * Duration in seconds
     */
    private Integer durationSeconds;

    /**
     * File size in bytes
     */
    private Long fileSizeBytes;

    /**
     * Active status (1=active, 0=inactive)
     */
    private Integer isActive;

    /**
     * Creation timestamp
     */
    private Date createdAt;

    /**
     * Last update timestamp
     */
    private Date updatedAt;

    @TableField(exist = false)
    private static final long serialVersionUID = 1L;

    /**
     * Content Type Enum
     */
    public enum ContentType {
        MUSIC("music"),
        STORY("story");

        private final String value;

        ContentType(String value) {
            this.value = value;
        }

        public String getValue() {
            return value;
        }

        public static ContentType fromValue(String value) {
            for (ContentType type : ContentType.values()) {
                if (type.value.equals(value)) {
                    return type;
                }
            }
            throw new IllegalArgumentException("Invalid ContentType value: " + value);
        }
    }
}
/**
 * Cloudflare R2 Storage Client
 * S3-compatible object storage with zero egress fees
 */
import { S3Client, PutObjectCommand, GetObjectCommand, DeleteObjectCommand, ListObjectsV2Command } from '@aws-sdk/client-s3';
import { Upload } from '@aws-sdk/lib-storage';
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';

// Initialize R2 client
const r2Client = new S3Client({
  region: 'auto',
  endpoint: `https://${process.env.R2_ACCOUNT_ID}.r2.cloudflarestorage.com`,
  credentials: {
    accessKeyId: process.env.R2_ACCESS_KEY_ID!,
    secretAccessKey: process.env.R2_SECRET_ACCESS_KEY!,
  },
});

const BUCKET_NAME = process.env.R2_BUCKET_NAME!;

/**
 * Upload a file to R2
 */
export async function uploadToR2(
  key: string,
  fileBuffer: Buffer,
  contentType: string
): Promise<{ success: boolean; key: string; error?: string }> {
  try {
    const upload = new Upload({
      client: r2Client,
      params: {
        Bucket: BUCKET_NAME,
        Key: key,
        Body: fileBuffer,
        ContentType: contentType,
      },
    });

    await upload.done();

    return {
      success: true,
      key: key,
    };
  } catch (error: any) {
    console.error('Error uploading to R2:', error);
    return {
      success: false,
      key: key,
      error: error.message || 'Upload failed',
    };
  }
}

/**
 * Download a file from R2
 */
export async function downloadFromR2(key: string): Promise<{
  success: boolean;
  data?: Buffer;
  contentType?: string;
  error?: string;
}> {
  try {
    const command = new GetObjectCommand({
      Bucket: BUCKET_NAME,
      Key: key,
    });

    const response = await r2Client.send(command);

    if (!response.Body) {
      return {
        success: false,
        error: 'No data returned',
      };
    }

    // Convert stream to buffer
    const chunks: Uint8Array[] = [];
    for await (const chunk of response.Body as any) {
      chunks.push(chunk);
    }
    const buffer = Buffer.concat(chunks);

    return {
      success: true,
      data: buffer,
      contentType: response.ContentType,
    };
  } catch (error: any) {
    console.error('Error downloading from R2:', error);
    return {
      success: false,
      error: error.message || 'Download failed',
    };
  }
}

/**
 * Delete a file from R2
 */
export async function deleteFromR2(key: string): Promise<{
  success: boolean;
  error?: string;
}> {
  try {
    const command = new DeleteObjectCommand({
      Bucket: BUCKET_NAME,
      Key: key,
    });

    await r2Client.send(command);

    return {
      success: true,
    };
  } catch (error: any) {
    console.error('Error deleting from R2:', error);
    return {
      success: false,
      error: error.message || 'Delete failed',
    };
  }
}

/**
 * List all files in R2 bucket (for debugging)
 */
export async function listR2Files(prefix?: string): Promise<{
  success: boolean;
  files?: Array<{ key: string; size: number; lastModified: Date }>;
  error?: string;
}> {
  try {
    const command = new ListObjectsV2Command({
      Bucket: BUCKET_NAME,
      Prefix: prefix,
    });

    const response = await r2Client.send(command);

    const files = response.Contents?.map(item => ({
      key: item.Key!,
      size: item.Size || 0,
      lastModified: item.LastModified || new Date(),
    })) || [];

    return {
      success: true,
      files,
    };
  } catch (error: any) {
    console.error('Error listing R2 files:', error);
    return {
      success: false,
      error: error.message || 'List failed',
    };
  }
}

/**
 * Get content type from file extension
 */
export function getContentType(fileType: string): string {
  const contentTypes: { [key: string]: string } = {
    'csv': 'text/csv',
    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'xls': 'application/vnd.ms-excel',
    'json': 'application/json',
    'txt': 'text/plain',
    'pdf': 'application/pdf',
    'png': 'image/png',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
  };

  return contentTypes[fileType.toLowerCase()] || 'application/octet-stream';
}

/**
 * Generate a unique file key for R2 storage
 */
export function generateR2Key(originalFilename: string): string {
  const timestamp = Date.now();
  const randomSuffix = Math.random().toString(36).substring(2, 8);
  const sanitizedName = originalFilename.replace(/[^a-zA-Z0-9._-]/g, '_');
  return `uploads/${timestamp}_${randomSuffix}_${sanitizedName}`;
}

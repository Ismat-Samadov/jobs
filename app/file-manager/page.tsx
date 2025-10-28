'use client';

import { useEffect, useState, useRef } from 'react';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';

export const dynamic = 'force-dynamic';

interface FileRecord {
  id: number;
  filename: string;
  original_filename: string;
  file_type: string;
  file_size: number;
  folder_id: number | null;
  folder_name: string | null;
  description: string | null;
  download_count: number;
  created_at: string;
  updated_at: string;
  uploaded_by: string;
}

interface Folder {
  id: number;
  name: string;
  parent_id: number | null;
  depth: number;
  file_count: number;
  subfolder_count: number;
  created_at: string;
}

export default function FileManagerPage() {
  const sessionData = useSession();
  const session = sessionData?.data;
  const status = sessionData?.status || 'loading';
  const router = useRouter();
  const [files, setFiles] = useState<FileRecord[]>([]);
  const [folders, setFolders] = useState<Folder[]>([]);
  const [currentFolder, setCurrentFolder] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [downloading, setDownloading] = useState<number | null>(null);

  // Modals
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [showCreateFolderModal, setShowCreateFolderModal] = useState(false);
  const [showEditFileModal, setShowEditFileModal] = useState(false);
  const [showEditFolderModal, setShowEditFolderModal] = useState(false);
  const [showMoveFileModal, setShowMoveFileModal] = useState(false);

  // Form states
  const [selectedFile, setSelectedFile] = useState<FileRecord | null>(null);
  const [selectedFolder, setSelectedFolder] = useState<Folder | null>(null);
  const [uploadFiles, setUploadFiles] = useState<File[]>([]);
  const [uploadDescription, setUploadDescription] = useState('');
  const [uploadProgress, setUploadProgress] = useState<string>('');
  const [folderName, setFolderName] = useState('');
  const [editFileName, setEditFileName] = useState('');
  const [editFileDescription, setEditFileDescription] = useState('');
  const [moveFolderId, setMoveFolderId] = useState<number | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (status === 'loading') return;

    if (status === 'unauthenticated' || !session) {
      router.push('/login');
      return;
    }

    if (session.user?.role !== 'admin') {
      router.push('/files');
      return;
    }

    fetchFolders();
    fetchFiles();
  }, [session, status, router, currentFolder]);

  const fetchFolders = async () => {
    try {
      const response = await fetch('/api/folders');
      const data = await response.json();
      setFolders(data.folders || []);
    } catch (error) {
      console.error('Error fetching folders:', error);
    }
  };

  const fetchFiles = async () => {
    try {
      const folderParam = currentFolder ? `?folderId=${currentFolder}` : '?folderId=root';
      const response = await fetch(`/api/files${folderParam}`);
      const data = await response.json();
      setFiles(data.files || []);
    } catch (error) {
      console.error('Error fetching files:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const filesArray = Array.from(e.target.files);
      setUploadFiles(filesArray);
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFiles || uploadFiles.length === 0) return;

    try {
      setUploading(true);
      const results = {
        uploaded: [] as any[],
        failed: [] as { filename: string; error: string }[],
        total: uploadFiles.length,
      };

      for (let i = 0; i < uploadFiles.length; i++) {
        const file = uploadFiles[i];
        try {
          setUploadProgress(`Uploading ${i + 1} of ${uploadFiles.length}: ${file.name}...`);

          // Step 1: Get presigned URL
          const urlResponse = await fetch('/api/files/upload-url', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              filename: file.name,
              contentType: file.type,
            }),
          });

          if (!urlResponse.ok) {
            throw new Error('Failed to get upload URL');
          }

          const { uploadUrl, key } = await urlResponse.json();

          // Step 2: Upload directly to R2
          const uploadResponse = await fetch(uploadUrl, {
            method: 'PUT',
            body: file,
            headers: {
              'Content-Type': file.type,
            },
          });

          if (!uploadResponse.ok) {
            throw new Error('Failed to upload file to storage');
          }

          // Step 3: Save metadata to database
          const metadataResponse = await fetch('/api/files/metadata', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              key,
              originalFilename: file.name,
              fileSize: file.size,
              folderId: currentFolder?.toString() || 'root',
              description: uploadDescription,
            }),
          });

          if (!metadataResponse.ok) {
            throw new Error('Failed to save file metadata');
          }

          const metadataResult = await metadataResponse.json();
          results.uploaded.push(metadataResult.file);
        } catch (error: any) {
          console.error(`Error uploading file ${file.name}:`, error);
          results.failed.push({
            filename: file.name,
            error: error.message || 'Upload failed',
          });
        }
      }

      // Show detailed results
      let message = '';
      if (results.uploaded.length > 0) {
        message += `✓ Successfully uploaded ${results.uploaded.length} file(s)`;
      }
      if (results.failed.length > 0) {
        message += `\n\n✗ Failed to upload ${results.failed.length} file(s):\n`;
        results.failed.forEach((f: any) => {
          message += `- ${f.filename}: ${f.error}\n`;
        });
      }

      alert(message || 'Files uploaded successfully');
      setShowUploadModal(false);
      setUploadFiles([]);
      setUploadDescription('');
      setUploadProgress('');
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      fetchFiles();
    } catch (error: any) {
      console.error('Error uploading files:', error);
      alert(error.message || 'Failed to upload files');
      setUploadProgress('');
    } finally {
      setUploading(false);
    }
  };

  const handleCreateFolder = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const response = await fetch('/api/folders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: folderName,
          parent_id: currentFolder,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Failed to create folder');
      }

      alert('Folder created successfully');
      setShowCreateFolderModal(false);
      setFolderName('');
      fetchFolders();
    } catch (error: any) {
      console.error('Error creating folder:', error);
      alert(error.message || 'Failed to create folder');
    }
  };

  const handleEditFile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;

    try {
      const response = await fetch('/api/files', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: selectedFile.id,
          original_filename: editFileName,
          description: editFileDescription,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to update file');
      }

      alert('File updated successfully');
      setShowEditFileModal(false);
      setSelectedFile(null);
      fetchFiles();
    } catch (error) {
      console.error('Error updating file:', error);
      alert('Failed to update file');
    }
  };

  const handleEditFolder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFolder) return;

    try {
      const response = await fetch('/api/folders', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: selectedFolder.id,
          name: folderName,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Failed to update folder');
      }

      alert('Folder updated successfully');
      setShowEditFolderModal(false);
      setSelectedFolder(null);
      setFolderName('');
      fetchFolders();
    } catch (error: any) {
      console.error('Error updating folder:', error);
      alert(error.message || 'Failed to update folder');
    }
  };

  const handleMoveFile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;

    try {
      const response = await fetch('/api/files', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: selectedFile.id,
          folder_id: moveFolderId || 'root',
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to move file');
      }

      alert('File moved successfully');
      setShowMoveFileModal(false);
      setSelectedFile(null);
      setMoveFolderId(null);
      fetchFiles();
    } catch (error) {
      console.error('Error moving file:', error);
      alert('Failed to move file');
    }
  };

  const handleDeleteFile = async (file: FileRecord) => {
    if (!confirm(`Are you sure you want to delete "${file.original_filename}"?`)) {
      return;
    }

    try {
      const response = await fetch(`/api/files?id=${file.id}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Failed to delete file');
      }

      alert('File deleted successfully');
      fetchFiles();
    } catch (error) {
      console.error('Error deleting file:', error);
      alert('Failed to delete file');
    }
  };

  const handleDeleteFolder = async (folder: Folder) => {
    if (!confirm(`Are you sure you want to delete the folder "${folder.name}"?`)) {
      return;
    }

    try {
      const response = await fetch(`/api/folders?id=${folder.id}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Failed to delete folder');
      }

      alert('Folder deleted successfully');
      fetchFolders();
    } catch (error: any) {
      console.error('Error deleting folder:', error);
      alert(error.message || 'Failed to delete folder');
    }
  };

  const handleDownload = async (fileId: number, filename: string) => {
    try {
      setDownloading(fileId);
      const response = await fetch(`/api/files/download?id=${fileId}`);

      if (!response.ok) {
        throw new Error('Download failed');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      fetchFiles();
    } catch (error) {
      console.error('Error downloading file:', error);
      alert('Failed to download file');
    } finally {
      setDownloading(null);
    }
  };

  const openEditFileModal = (file: FileRecord) => {
    setSelectedFile(file);
    setEditFileName(file.original_filename);
    setEditFileDescription(file.description || '');
    setShowEditFileModal(true);
  };

  const openEditFolderModal = (folder: Folder) => {
    setSelectedFolder(folder);
    setFolderName(folder.name);
    setShowEditFolderModal(true);
  };

  const openMoveFileModal = (file: FileRecord) => {
    setSelectedFile(file);
    setMoveFolderId(file.folder_id);
    setShowMoveFileModal(true);
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const getFileIcon = (fileType: string) => {
    const icons: { [key: string]: JSX.Element } = {
      csv: (
        <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      ),
      xlsx: (
        <svg className="w-8 h-8 text-green-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
        </svg>
      ),
      json: (
        <svg className="w-8 h-8 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
        </svg>
      ),
    };

    return icons[fileType] || (
      <svg className="w-8 h-8 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
      </svg>
    );
  };

  const getCurrentFolderName = (): string => {
    if (!currentFolder) return 'Root';
    const folder = folders.find(f => f.id === currentFolder);
    return folder ? folder.name : 'Unknown';
  };

  const getBreadcrumbs = (): Folder[] => {
    if (!currentFolder) return [];

    const breadcrumbs: Folder[] = [];
    let folder = folders.find(f => f.id === currentFolder);

    while (folder) {
      breadcrumbs.unshift(folder);
      folder = folders.find(f => f.id === folder!.parent_id);
    }

    return breadcrumbs;
  };

  const getSubfolders = (): Folder[] => {
    return folders.filter(f => f.parent_id === currentFolder);
  };

  const getAvailableFolders = (): Folder[] => {
    // For move operation, show all folders except the file's current folder
    return folders.filter(f => f.id !== selectedFile?.folder_id);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="text-xl font-semibold text-gray-700">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation Header */}
      <nav className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-3">
              <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
              </svg>
              <h1 className="text-lg font-semibold text-gray-900">File Manager</h1>
            </div>
            <div className="flex items-center space-x-2">
              <a href="/dashboard" className="px-3 py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-md">Dashboard</a>
              <a href="/files" className="px-3 py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-md">Files</a>
              <a href="/api/auth/signout" className="px-3 py-2 text-sm text-red-600 hover:text-red-700 hover:bg-red-50 rounded-md">Logout</a>
            </div>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Action Buttons & Breadcrumbs */}
        <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          {/* Breadcrumb Navigation */}
          <div className="flex items-center space-x-2 text-sm">
            <button
              onClick={() => setCurrentFolder(null)}
              className="px-3 py-1.5 text-blue-600 hover:bg-blue-50 rounded-md font-medium"
            >
              Root
            </button>
            {getBreadcrumbs().map((folder) => (
              <div key={folder.id} className="flex items-center space-x-2">
                <span className="text-gray-400">/</span>
                <button
                  onClick={() => setCurrentFolder(folder.id)}
                  className="px-3 py-1.5 text-gray-700 hover:bg-gray-100 rounded-md"
                >
                  {folder.name}
                </button>
              </div>
            ))}
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowCreateFolderModal(true)}
              className="inline-flex items-center px-4 py-2 bg-white border border-gray-300 text-gray-700 text-sm font-medium rounded-md hover:bg-gray-50"
            >
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 13h6m-3-3v6m-9 1V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
              </svg>
              New Folder
            </button>
            <button
              onClick={() => setShowUploadModal(true)}
              className="inline-flex items-center px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700"
            >
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              Upload Files
            </button>
          </div>
        </div>

        {/* Folders */}
        {getSubfolders().length > 0 && (
          <div className="mb-6">
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
              {getSubfolders().map((folder) => (
                <div
                  key={folder.id}
                  className="bg-white border border-gray-200 rounded-lg p-4 hover:border-blue-300 hover:shadow-sm transition-all group"
                >
                  <button
                    onClick={() => setCurrentFolder(folder.id)}
                    className="w-full text-left"
                  >
                    <div className="flex items-start space-x-3">
                      <svg className="w-10 h-10 text-blue-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                      </svg>
                      <div className="flex-1 min-w-0 mt-1">
                        <h3 className="text-sm font-medium text-gray-900 truncate">{folder.name}</h3>
                      </div>
                    </div>
                  </button>
                  <div className="flex space-x-1 mt-3 pt-3 border-t border-gray-100">
                    <button
                      onClick={() => openEditFolderModal(folder)}
                      className="flex-1 px-2 py-1.5 text-xs text-gray-600 hover:bg-gray-100 rounded"
                      title="Rename"
                    >
                      Rename
                    </button>
                    <button
                      onClick={() => handleDeleteFolder(folder)}
                      className="flex-1 px-2 py-1.5 text-xs text-red-600 hover:bg-red-50 rounded"
                      title="Delete"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Files */}
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          {files.length === 0 ? (
            <div className="p-12 text-center text-gray-500">
              <svg className="mx-auto h-12 w-12 text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
              </svg>
              <p className="text-sm">No files in this folder</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-200">
              {files.map((file) => (
                <div key={file.id} className="p-4 hover:bg-gray-50 transition-colors">
                  <div className="flex items-center justify-between gap-4">
                    {/* File Info */}
                    <div className="flex items-center space-x-3 flex-1 min-w-0">
                      <div className="flex-shrink-0">
                        {getFileIcon(file.file_type)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="text-sm font-medium text-gray-900 truncate">{file.original_filename}</h3>
                        <div className="flex items-center space-x-4 mt-1 text-xs text-gray-500">
                          <span>{formatFileSize(file.file_size)}</span>
                          <span>{new Date(file.created_at).toLocaleDateString()}</span>
                          <span>{file.download_count} downloads</span>
                        </div>
                        {file.description && (
                          <p className="text-xs text-gray-600 mt-1">{file.description}</p>
                        )}
                      </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleDownload(file.id, file.original_filename)}
                        disabled={downloading === file.id}
                        className="px-3 py-1.5 text-xs font-medium text-blue-600 hover:bg-blue-50 rounded disabled:opacity-50"
                      >
                        {downloading === file.id ? 'Downloading...' : 'Download'}
                      </button>
                      <button
                        onClick={() => openEditFileModal(file)}
                        className="px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-100 rounded"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => openMoveFileModal(file)}
                        className="px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-100 rounded"
                      >
                        Move
                      </button>
                      <button
                        onClick={() => handleDeleteFile(file)}
                        className="px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 rounded"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Upload File Modal */}
      {showUploadModal && (
        <div className="fixed z-50 inset-0 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            <div className="fixed inset-0 bg-gray-900/80 backdrop-blur-sm transition-opacity" onClick={() => !uploading && setShowUploadModal(false)}></div>
            <div className="inline-block align-bottom bg-white rounded-2xl text-left overflow-hidden shadow-2xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
              <form onSubmit={handleUpload}>
                <div className="bg-gradient-to-r from-blue-50 to-purple-50 px-6 pt-6 pb-4">
                  <h3 className="text-xl font-bold text-gray-900">Upload Files</h3>
                  <p className="text-sm text-gray-600 mt-1">Upload one or multiple files at once</p>
                </div>
                <div className="bg-white px-6 pt-4 pb-6">
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-2">
                        Select File(s)
                      </label>
                      <input
                        ref={fileInputRef}
                        type="file"
                        accept=".csv,.xlsx,.xls,.json,.txt"
                        onChange={handleFileSelect}
                        multiple
                        required
                        disabled={uploading}
                        className="block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-white focus:outline-none p-2 disabled:opacity-50 disabled:cursor-not-allowed"
                      />
                      <p className="mt-1 text-xs text-gray-500">
                        Supported formats: CSV, XLSX, XLS, JSON, TXT. You can select multiple files.
                      </p>
                      {uploadFiles.length > 0 && (
                        <div className="mt-3 p-3 bg-blue-50 rounded-lg">
                          <p className="text-sm font-semibold text-blue-900 mb-2">
                            Selected {uploadFiles.length} file(s):
                          </p>
                          <ul className="text-xs text-blue-700 space-y-1 max-h-32 overflow-y-auto">
                            {uploadFiles.map((file, index) => (
                              <li key={index} className="truncate">
                                • {file.name} ({(file.size / 1024).toFixed(1)} KB)
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-2">
                        Description (Optional)
                      </label>
                      <textarea
                        value={uploadDescription}
                        onChange={(e) => setUploadDescription(e.target.value)}
                        rows={3}
                        disabled={uploading}
                        className="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900 disabled:opacity-50"
                        placeholder="Enter description (will apply to all files)..."
                      />
                    </div>
                    {uploading && uploadProgress && (
                      <div className="p-3 bg-green-50 rounded-lg">
                        <div className="flex items-center space-x-2">
                          <svg className="animate-spin w-5 h-5 text-green-600" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                          <p className="text-sm font-semibold text-green-900">{uploadProgress}</p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
                <div className="bg-gray-50 px-6 py-4 flex justify-end space-x-3">
                  <button
                    type="button"
                    onClick={() => {
                      setShowUploadModal(false);
                      setUploadFiles([]);
                      setUploadDescription('');
                      setUploadProgress('');
                      if (fileInputRef.current) {
                        fileInputRef.current.value = '';
                      }
                    }}
                    disabled={uploading}
                    className="px-4 py-2 text-sm font-semibold text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={uploading || uploadFiles.length === 0}
                    className="px-4 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {uploading ? 'Uploading...' : `Upload ${uploadFiles.length} file(s)`}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Create Folder Modal */}
      {showCreateFolderModal && (
        <div className="fixed z-50 inset-0 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            <div className="fixed inset-0 bg-gray-900/80 backdrop-blur-sm transition-opacity" onClick={() => setShowCreateFolderModal(false)}></div>
            <div className="inline-block align-bottom bg-white rounded-2xl text-left overflow-hidden shadow-2xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
              <form onSubmit={handleCreateFolder}>
                <div className="bg-gradient-to-r from-purple-50 to-pink-50 px-6 pt-6 pb-4">
                  <h3 className="text-xl font-bold text-gray-900">Create New Folder</h3>
                </div>
                <div className="bg-white px-6 pt-4 pb-6">
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    Folder Name
                  </label>
                  <input
                    type="text"
                    value={folderName}
                    onChange={(e) => setFolderName(e.target.value)}
                    required
                    className="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 text-gray-900"
                    placeholder="Enter folder name..."
                  />
                </div>
                <div className="bg-gray-50 px-6 py-4 flex justify-end space-x-3">
                  <button
                    type="button"
                    onClick={() => {
                      setShowCreateFolderModal(false);
                      setFolderName('');
                    }}
                    className="px-4 py-2 text-sm font-semibold text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 text-sm font-semibold text-white bg-purple-600 hover:bg-purple-700 rounded-lg"
                  >
                    Create
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Edit File Modal */}
      {showEditFileModal && selectedFile && (
        <div className="fixed z-50 inset-0 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            <div className="fixed inset-0 bg-gray-900/80 backdrop-blur-sm transition-opacity" onClick={() => setShowEditFileModal(false)}></div>
            <div className="inline-block align-bottom bg-white rounded-2xl text-left overflow-hidden shadow-2xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
              <form onSubmit={handleEditFile}>
                <div className="bg-gradient-to-r from-blue-50 to-purple-50 px-6 pt-6 pb-4">
                  <h3 className="text-xl font-bold text-gray-900">Edit File</h3>
                </div>
                <div className="bg-white px-6 pt-4 pb-6 space-y-4">
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">
                      File Name
                    </label>
                    <input
                      type="text"
                      value={editFileName}
                      onChange={(e) => setEditFileName(e.target.value)}
                      required
                      className="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">
                      Description
                    </label>
                    <textarea
                      value={editFileDescription}
                      onChange={(e) => setEditFileDescription(e.target.value)}
                      rows={3}
                      className="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900"
                    />
                  </div>
                </div>
                <div className="bg-gray-50 px-6 py-4 flex justify-end space-x-3">
                  <button
                    type="button"
                    onClick={() => {
                      setShowEditFileModal(false);
                      setSelectedFile(null);
                    }}
                    className="px-4 py-2 text-sm font-semibold text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg"
                  >
                    Save
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Edit Folder Modal */}
      {showEditFolderModal && selectedFolder && (
        <div className="fixed z-50 inset-0 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            <div className="fixed inset-0 bg-gray-900/80 backdrop-blur-sm transition-opacity" onClick={() => setShowEditFolderModal(false)}></div>
            <div className="inline-block align-bottom bg-white rounded-2xl text-left overflow-hidden shadow-2xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
              <form onSubmit={handleEditFolder}>
                <div className="bg-gradient-to-r from-purple-50 to-pink-50 px-6 pt-6 pb-4">
                  <h3 className="text-xl font-bold text-gray-900">Rename Folder</h3>
                </div>
                <div className="bg-white px-6 pt-4 pb-6">
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    Folder Name
                  </label>
                  <input
                    type="text"
                    value={folderName}
                    onChange={(e) => setFolderName(e.target.value)}
                    required
                    className="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 text-gray-900"
                  />
                </div>
                <div className="bg-gray-50 px-6 py-4 flex justify-end space-x-3">
                  <button
                    type="button"
                    onClick={() => {
                      setShowEditFolderModal(false);
                      setSelectedFolder(null);
                      setFolderName('');
                    }}
                    className="px-4 py-2 text-sm font-semibold text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 text-sm font-semibold text-white bg-purple-600 hover:bg-purple-700 rounded-lg"
                  >
                    Save
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Move File Modal */}
      {showMoveFileModal && selectedFile && (
        <div className="fixed z-50 inset-0 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            <div className="fixed inset-0 bg-gray-900/80 backdrop-blur-sm transition-opacity" onClick={() => setShowMoveFileModal(false)}></div>
            <div className="inline-block align-bottom bg-white rounded-2xl text-left overflow-hidden shadow-2xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
              <form onSubmit={handleMoveFile}>
                <div className="bg-gradient-to-r from-purple-50 to-pink-50 px-6 pt-6 pb-4">
                  <h3 className="text-xl font-bold text-gray-900">Move File</h3>
                </div>
                <div className="bg-white px-6 pt-4 pb-6">
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    Move to Folder
                  </label>
                  <select
                    value={moveFolderId || 'root'}
                    onChange={(e) => setMoveFolderId(e.target.value === 'root' ? null : parseInt(e.target.value))}
                    className="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 text-gray-900"
                  >
                    <option value="root">Root</option>
                    {getAvailableFolders().map((folder) => (
                      <option key={folder.id} value={folder.id}>
                        {'  '.repeat(folder.depth) + folder.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="bg-gray-50 px-6 py-4 flex justify-end space-x-3">
                  <button
                    type="button"
                    onClick={() => {
                      setShowMoveFileModal(false);
                      setSelectedFile(null);
                      setMoveFolderId(null);
                    }}
                    className="px-4 py-2 text-sm font-semibold text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 text-sm font-semibold text-white bg-purple-600 hover:bg-purple-700 rounded-lg"
                  >
                    Move
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

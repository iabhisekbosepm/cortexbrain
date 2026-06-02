"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { cn } from "@/lib/utils";

const MAX_FILE_SIZE = 20 * 1024 * 1024; // 20 MB

const IMAGE_EXTENSIONS = new Set([
  ".png", ".jpg", ".jpeg", ".gif", ".webp", ".tiff", ".tif", ".bmp", ".heic", ".avif",
]);

function isImageFile(file: File): boolean {
  const ext = "." + file.name.split(".").pop()?.toLowerCase();
  return IMAGE_EXTENSIONS.has(ext) || file.type.startsWith("image/");
}

interface FileUploadZoneProps {
  files: File[];
  onFilesChange: (files: File[]) => void;
  accept?: string;
  onSizeError?: (fileName: string) => void;
}

export function FileUploadZone({
  files,
  onFilesChange,
  accept = ".pdf,.md,.txt,.png,.jpg,.jpeg,.gif,.webp,.tiff,.tif,.bmp,.heic,.avif",
  onSizeError,
}: FileUploadZoneProps) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const [previews, setPreviews] = useState<Map<number, string>>(new Map());

  const filterBySize = useCallback(
    (incoming: File[]): File[] => {
      const valid: File[] = [];
      for (const f of incoming) {
        if (f.size > MAX_FILE_SIZE) {
          onSizeError?.(f.name);
        } else {
          valid.push(f);
        }
      }
      return valid;
    },
    [onSizeError],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const dropped = filterBySize(Array.from(e.dataTransfer.files));
      if (dropped.length > 0) onFilesChange([...files, ...dropped]);
    },
    [files, onFilesChange, filterBySize],
  );

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files) {
        const accepted = filterBySize(Array.from(e.target.files));
        if (accepted.length > 0) onFilesChange([...files, ...accepted]);
      }
    },
    [files, onFilesChange, filterBySize],
  );

  // Generate object URLs for image previews
  useEffect(() => {
    const newPreviews = new Map<number, string>();
    files.forEach((file, i) => {
      if (isImageFile(file)) {
        newPreviews.set(i, URL.createObjectURL(file));
      }
    });
    setPreviews(newPreviews);
    return () => {
      newPreviews.forEach((url) => URL.revokeObjectURL(url));
    };
  }, [files]);

  function removeFile(index: number) {
    onFilesChange(files.filter((_, i) => i !== index));
  }

  return (
    <div className="space-y-3">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={cn(
          "flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 cursor-pointer transition-colors",
          dragging
            ? "border-copper-500 bg-copper-50"
            : "border-gray-300 bg-white hover:border-gray-400",
        )}
      >
        <svg className="h-10 w-10 text-gray-400 mb-3" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 16.5V9.75m0 0l3 3m-3-3l-3 3M6.75 19.5a4.5 4.5 0 01-1.41-8.775 5.25 5.25 0 0110.233-2.33 3 3 0 013.758 3.848A3.752 3.752 0 0118 19.5H6.75z" />
        </svg>
        <p className="text-sm text-gray-600 font-medium">Drop files here or click to browse</p>
        <p className="text-xs text-gray-400 mt-1">Supports PDF, Markdown, text, and image files</p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={accept}
          onChange={handleFileInput}
          className="hidden"
        />
      </div>

      {files.length > 0 && (
        <div className="space-y-2">
          {files.map((file, i) => (
            <div key={i} className="flex items-center justify-between rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm">
              <div className="flex items-center gap-2 min-w-0">
                {previews.has(i) ? (
                  <img
                    src={previews.get(i)}
                    alt={file.name}
                    className="h-8 w-8 rounded object-cover shrink-0"
                  />
                ) : (
                  <svg className="h-4 w-4 text-gray-400 shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                  </svg>
                )}
                <span className="truncate">{file.name}</span>
                <span className="text-gray-400 shrink-0">
                  ({file.size >= 1024 * 1024
                    ? (file.size / (1024 * 1024)).toFixed(1) + " MB"
                    : (file.size / 1024).toFixed(1) + " KB"})
                </span>
              </div>
              <button onClick={() => removeFile(i)} className="text-gray-400 hover:text-red-500 ml-2">
                &times;
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

"use client";

import { useState, useEffect, useCallback } from "react";
import { PageShell } from "@/components/layout/page-shell";
import { getDatasets, getDatasetData, getDataItemContent } from "@/lib/api/datasets";
import { formatDate } from "@/lib/utils";
import type { DatasetEntry, DatasetDataItem } from "@/lib/types";

export default function DatasetsPage() {
  const [datasets, setDatasets] = useState<DatasetEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  // Selected dataset
  const [selected, setSelected] = useState<string | null>(null);
  const [dataItems, setDataItems] = useState<DatasetDataItem[]>([]);
  const [dataLoading, setDataLoading] = useState(false);
  const [dataError, setDataError] = useState<string | null>(null);
  const [dataTotal, setDataTotal] = useState(0);

  // Content viewer
  const [viewingId, setViewingId] = useState<string | null>(null);
  const [content, setContent] = useState<string | null>(null);
  const [contentName, setContentName] = useState("");
  const [contentLoading, setContentLoading] = useState(false);
  const [contentError, setContentError] = useState<string | null>(null);
  const [contentTruncated, setContentTruncated] = useState(false);

  const loadDatasets = useCallback(async (filter?: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await getDatasets(filter || undefined);
      setDatasets(res.datasets);
      setTotal(res.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load datasets");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDatasets();
  }, [loadDatasets]);

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      loadDatasets(search);
    }, 300);
    return () => clearTimeout(timer);
  }, [search, loadDatasets]);

  async function handleSelect(name: string) {
    setSelected(name);
    setDataLoading(true);
    setDataError(null);
    setDataItems([]);
    setViewingId(null);
    setContent(null);
    try {
      const res = await getDatasetData(name);
      setDataItems(res.data);
      setDataTotal(res.total);
    } catch (e) {
      setDataError(e instanceof Error ? e.message : "Failed to load data items");
    } finally {
      setDataLoading(false);
    }
  }

  async function handleViewContent(dataId: string, name: string) {
    if (viewingId === dataId) {
      // Toggle off
      setViewingId(null);
      setContent(null);
      return;
    }
    setViewingId(dataId);
    setContentName(name);
    setContentLoading(true);
    setContentError(null);
    setContent(null);
    try {
      const res = await getDataItemContent(dataId);
      setContent(res.content);
      setContentTruncated(res.truncated);
    } catch (e) {
      setContentError(e instanceof Error ? e.message : "Failed to load content");
    } finally {
      setContentLoading(false);
    }
  }

  function formatSize(bytes: number | null): string {
    if (bytes === null || bytes === undefined) return "-";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  return (
    <PageShell
      title="Datasets"
      description="Browse ingested knowledge sources and their data items"
      actions={
        <button
          onClick={() => { setSearch(""); loadDatasets(); setSelected(null); setViewingId(null); setContent(null); }}
          className="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
        >
          Refresh
        </button>
      }
    >
      <div className="flex gap-6 h-[calc(100vh-12rem)]">
        {/* Left: Dataset List */}
        <div className="w-80 shrink-0 flex flex-col border border-gray-200 rounded-xl bg-white overflow-hidden">
          {/* Search */}
          <div className="p-3 border-b border-gray-200">
            <input
              type="text"
              placeholder="Search datasets..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm placeholder:text-gray-400 focus:border-copper-500 focus:outline-none focus:ring-1 focus:ring-copper-500"
            />
          </div>

          {/* List */}
          <div className="flex-1 overflow-y-auto">
            {loading && datasets.length === 0 && (
              <div className="flex items-center justify-center py-12">
                <svg className="h-5 w-5 animate-spin text-copper-600" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
              </div>
            )}

            {error && (
              <div className="p-4 text-sm text-red-600">{error}</div>
            )}

            {!loading && !error && datasets.length === 0 && (
              <div className="p-6 text-center text-sm text-gray-400">
                No datasets found
              </div>
            )}

            {datasets.map((ds) => (
              <button
                key={ds.id}
                onClick={() => handleSelect(ds.name)}
                className={`w-full text-left px-4 py-3 border-b border-gray-100 transition-colors ${
                  selected === ds.name
                    ? "bg-copper-50 border-l-2 border-l-copper-500"
                    : "hover:bg-gray-50"
                }`}
              >
                <div className="flex items-center gap-2">
                  <svg className="h-4 w-4 text-gray-400 shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125v-3.75" />
                  </svg>
                  <span className="text-sm font-medium text-gray-900 truncate">{ds.name}</span>
                </div>
                {ds.created_at && (
                  <p className="mt-1 text-[11px] text-gray-400 ml-6">
                    Created {formatDate(ds.created_at)}
                  </p>
                )}
              </button>
            ))}
          </div>

          {/* Footer */}
          <div className="px-4 py-2 border-t border-gray-200 bg-gray-50 text-[11px] text-gray-500">
            {total} dataset{total !== 1 ? "s" : ""}
          </div>
        </div>

        {/* Right: Data Items + Content Viewer */}
        <div className="flex-1 flex flex-col border border-gray-200 rounded-xl bg-white overflow-hidden">
          {!selected && (
            <div className="flex-1 flex items-center justify-center text-gray-400 text-sm">
              Select a dataset to view its data items
            </div>
          )}

          {selected && (
            <>
              {/* Header */}
              <div className="px-5 py-3 border-b border-gray-200 flex items-center justify-between shrink-0">
                <div>
                  <h3 className="text-sm font-semibold text-gray-900">{selected}</h3>
                  <p className="text-[11px] text-gray-500">{dataTotal} data item{dataTotal !== 1 ? "s" : ""}</p>
                </div>
                <button
                  onClick={() => { setSelected(null); setViewingId(null); setContent(null); }}
                  className="text-gray-400 hover:text-gray-600 transition-colors"
                >
                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* Table */}
              <div className={`overflow-auto ${viewingId ? "max-h-[40%]" : "flex-1"} shrink-0`}>
                {dataLoading && (
                  <div className="flex items-center justify-center py-12">
                    <svg className="h-5 w-5 animate-spin text-copper-600" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                  </div>
                )}

                {dataError && (
                  <div className="p-4 text-sm text-red-600">{dataError}</div>
                )}

                {!dataLoading && !dataError && dataItems.length === 0 && (
                  <div className="p-6 text-center text-sm text-gray-400">
                    No data items in this dataset
                  </div>
                )}

                {!dataLoading && !dataError && dataItems.length > 0 && (
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-200 bg-gray-50 text-left text-[11px] font-medium uppercase tracking-wider text-gray-500">
                        <th className="px-4 py-2">Name</th>
                        <th className="px-4 py-2">Type</th>
                        <th className="px-4 py-2 text-right">Tokens</th>
                        <th className="px-4 py-2 text-right">Size</th>
                        <th className="px-4 py-2">Created</th>
                        <th className="px-4 py-2 text-center">Content</th>
                      </tr>
                    </thead>
                    <tbody>
                      {dataItems.map((item) => (
                        <tr
                          key={item.id}
                          className={`border-b border-gray-100 transition-colors ${
                            viewingId === item.id ? "bg-copper-50" : "hover:bg-gray-50"
                          }`}
                        >
                          <td className="px-4 py-2.5">
                            <div className="flex items-center gap-2">
                              <span className="text-gray-900 font-medium truncate max-w-[250px]" title={item.name}>
                                {item.name}
                              </span>
                              {item.label && (
                                <span className="inline-flex rounded-full bg-gray-100 px-2 py-0.5 text-[10px] text-gray-600">
                                  {item.label}
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="px-4 py-2.5">
                            <span className="inline-flex rounded-md bg-blue-50 border border-blue-100 px-2 py-0.5 text-[11px] text-blue-700">
                              {item.extension || item.mime_type || "-"}
                            </span>
                          </td>
                          <td className="px-4 py-2.5 text-right text-gray-600 tabular-nums">
                            {item.token_count !== null ? item.token_count.toLocaleString() : "-"}
                          </td>
                          <td className="px-4 py-2.5 text-right text-gray-600 tabular-nums">
                            {formatSize(item.data_size)}
                          </td>
                          <td className="px-4 py-2.5 text-gray-500 text-[11px]">
                            {item.created_at ? formatDate(item.created_at) : "-"}
                          </td>
                          <td className="px-4 py-2.5 text-center">
                            <button
                              onClick={() => handleViewContent(item.id, item.name)}
                              className={`inline-flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-medium transition-colors ${
                                viewingId === item.id
                                  ? "bg-copper-600 text-white"
                                  : "bg-gray-100 text-gray-600 hover:bg-copper-100 hover:text-copper-700"
                              }`}
                            >
                              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
                                <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                              </svg>
                              {viewingId === item.id ? "Hide" : "View"}
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>

              {/* Content Viewer Panel */}
              {viewingId && (
                <div className="flex-1 border-t border-gray-200 flex flex-col min-h-0">
                  <div className="px-4 py-2 bg-gray-50 border-b border-gray-200 flex items-center justify-between shrink-0">
                    <div className="flex items-center gap-2">
                      <svg className="h-4 w-4 text-copper-600" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                      </svg>
                      <span className="text-xs font-medium text-gray-700 truncate max-w-[300px]">{contentName}</span>
                      {contentTruncated && (
                        <span className="inline-flex rounded-full bg-yellow-50 border border-yellow-200 px-2 py-0.5 text-[10px] text-yellow-700">
                          Truncated (50K chars)
                        </span>
                      )}
                    </div>
                    <button
                      onClick={() => { setViewingId(null); setContent(null); }}
                      className="text-gray-400 hover:text-gray-600 transition-colors"
                    >
                      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                  <div className="flex-1 overflow-auto p-4">
                    {contentLoading && (
                      <div className="flex items-center gap-2 py-4">
                        <svg className="h-4 w-4 animate-spin text-copper-600" viewBox="0 0 24 24" fill="none">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                        <span className="text-sm text-gray-500">Loading content...</span>
                      </div>
                    )}
                    {contentError && (
                      <div className="text-sm text-red-600">{contentError}</div>
                    )}
                    {content !== null && !contentLoading && (
                      <pre className="text-xs text-gray-800 whitespace-pre-wrap break-words font-mono leading-relaxed">
                        {content}
                      </pre>
                    )}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </PageShell>
  );
}

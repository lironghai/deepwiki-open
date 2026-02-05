'use client';

import React, { useState, useEffect } from 'react';
import Markdown from '@/components/Markdown';
import { FaSave, FaTimes, FaEdit, FaEye } from 'react-icons/fa';

interface WikiEditorProps {
  pageId: string;
  initialTitle: string;
  initialContent: string;
  onSave: (pageId: string, title: string, content: string) => Promise<void>;
  onCancel: () => void;
  isSaving?: boolean;
}

const WikiEditor: React.FC<WikiEditorProps> = ({
  pageId,
  initialTitle,
  initialContent,
  onSave,
  onCancel,
  isSaving = false,
}) => {
  const [title, setTitle] = useState(initialTitle);
  const [content, setContent] = useState(initialContent);
  const [viewMode, setViewMode] = useState<'edit' | 'preview' | 'split'>('edit');
  const [hasChanges, setHasChanges] = useState(false);

  // Track changes
  useEffect(() => {
    const titleChanged = title !== initialTitle;
    const contentChanged = content !== initialContent;
    setHasChanges(titleChanged || contentChanged);
  }, [title, content, initialTitle, initialContent]);

  const handleSave = async () => {
    if (!hasChanges) {
      onCancel();
      return;
    }
    await onSave(pageId, title, content);
  };

  const handleCancel = () => {
    if (hasChanges) {
      const confirmed = window.confirm('您有未保存的更改，确定要取消吗？');
      if (!confirmed) return;
    }
    setTitle(initialTitle);
    setContent(initialContent);
    onCancel();
  };

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-[var(--border-color)]">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setViewMode('edit')}
            className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
              viewMode === 'edit'
                ? 'bg-[var(--accent-primary)] text-white'
                : 'bg-[var(--card-bg)] text-[var(--foreground)] hover:bg-[var(--background)]'
            }`}
          >
            <FaEdit className="inline-block mr-1.5" />
            编辑
          </button>
          <button
            onClick={() => setViewMode('preview')}
            className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
              viewMode === 'preview'
                ? 'bg-[var(--accent-primary)] text-white'
                : 'bg-[var(--card-bg)] text-[var(--foreground)] hover:bg-[var(--background)]'
            }`}
          >
            <FaEye className="inline-block mr-1.5" />
            预览
          </button>
          <button
            onClick={() => setViewMode('split')}
            className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
              viewMode === 'split'
                ? 'bg-[var(--accent-primary)] text-white'
                : 'bg-[var(--card-bg)] text-[var(--foreground)] hover:bg-[var(--background)]'
            }`}
          >
            分屏
          </button>
        </div>
        <div className="flex items-center gap-2">
          {hasChanges && (
            <span className="text-xs text-[var(--muted)]">有未保存的更改</span>
          )}
          <button
            onClick={handleCancel}
            disabled={isSaving}
            className="px-4 py-2 rounded-md bg-[var(--card-bg)] text-[var(--foreground)] hover:bg-[var(--background)] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <FaTimes />
            取消
          </button>
          <button
            onClick={handleSave}
            disabled={isSaving || !hasChanges}
            className="px-4 py-2 rounded-md bg-[var(--accent-primary)] text-white hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {isSaving ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                保存中...
              </>
            ) : (
              <>
                <FaSave />
                保存
              </>
            )}
          </button>
        </div>
      </div>

      {/* Title Input */}
      <div className="mb-4">
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="页面标题"
          className="w-full px-4 py-2 text-xl font-bold bg-[var(--card-bg)] border border-[var(--border-color)] rounded-md text-[var(--foreground)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)]"
        />
      </div>

      {/* Editor/Preview Content */}
      <div className="flex-1 flex gap-4 min-h-0">
        {/* Edit Mode */}
        {(viewMode === 'edit' || viewMode === 'split') && (
          <div className={`flex-1 flex flex-col ${viewMode === 'split' ? 'w-1/2' : 'w-full'}`}>
            <label className="text-sm font-medium text-[var(--muted)] mb-2">编辑内容 (Markdown)</label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="在此输入Markdown内容..."
              className="flex-1 w-full px-4 py-3 font-mono text-sm bg-[var(--card-bg)] border border-[var(--border-color)] rounded-md text-[var(--foreground)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)] resize-none"
              style={{ minHeight: '400px' }}
            />
          </div>
        )}

        {/* Preview Mode */}
        {(viewMode === 'preview' || viewMode === 'split') && (
          <div className={`flex-1 flex flex-col overflow-y-auto ${viewMode === 'split' ? 'w-1/2 border-l border-[var(--border-color)] pl-4' : 'w-full'}`}>
            <label className="text-sm font-medium text-[var(--muted)] mb-2">预览</label>
            <div className="flex-1 bg-[var(--card-bg)] rounded-md p-4">
              <h3 className="text-xl font-bold text-[var(--foreground)] mb-4 break-words font-serif">
                {title || '未命名页面'}
              </h3>
              <div className="prose prose-sm md:prose-base lg:prose-lg max-w-none">
                <Markdown content={content || '*暂无内容*'} />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default WikiEditor;

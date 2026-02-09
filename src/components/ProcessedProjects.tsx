'use client';

import React, { useState, useMemo, useDeferredValue } from 'react';
import Link from 'next/link';
import { FaTimes, FaTh, FaList } from 'react-icons/fa';
import type { ProcessedProject } from '@/types/processedProject';

interface ProcessedProjectsProps {
  showHeader?: boolean;
  maxItems?: number;
  className?: string;
  messages?: Record<string, Record<string, string>>; // Translation messages with proper typing
  projects: ProcessedProject[];
  isLoading: boolean;
  error: string | null;
  setProjects: React.Dispatch<React.SetStateAction<ProcessedProject[]>>;
}

export default function ProcessedProjects({ 
  showHeader = true, 
  maxItems, 
  className = "",
  messages,
  projects,
  isLoading,
  error,
  setProjects
}: ProcessedProjectsProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState<'card' | 'list'>('card');
  const deferredSearchQuery = useDeferredValue(searchQuery);

  // Default messages fallback
  const defaultMessages = {
    title: 'Processed Wiki Projects',
    searchPlaceholder: 'Search projects by name, owner, or repository...',
    noProjects: 'No projects found in the server cache. The cache might be empty or the server encountered an issue.',
    noSearchResults: 'No projects match your search criteria.',
    processedOn: 'Processed on:',
    loadingProjects: 'Loading projects...',
    errorLoading: 'Error loading projects:',
    backToHome: 'Back to Home'
  };

  const t = (key: string) => {
    if (messages?.projects?.[key]) {
      return messages.projects[key];
    }
    return defaultMessages[key as keyof typeof defaultMessages] || key;
  };

  const dateFormatter = useMemo(() => {
    return new Intl.DateTimeFormat(undefined, {
      year: 'numeric',
      month: 'short',
      day: '2-digit',
    });
  }, []);

  const indexedProjects = useMemo(() => {
    return projects.map((project) => ({
      project,
      searchKey: `${project.name} ${project.owner} ${project.repo} ${project.repo_type}`.toLowerCase(),
    }));
  }, [projects]);

  // Filter projects based on search query
  const filteredProjects = useMemo(() => {
    const query = deferredSearchQuery.trim().toLowerCase();
    if (!query) {
      return maxItems ? projects.slice(0, maxItems) : projects;
    }

    const filtered = indexedProjects
      .filter(({ searchKey }) => searchKey.includes(query))
      .map(({ project }) => project);

    return maxItems ? filtered.slice(0, maxItems) : filtered;
  }, [projects, indexedProjects, deferredSearchQuery, maxItems]);

  const preparedProjects = useMemo(() => {
    return filteredProjects.map((project) => {
      return {
        ...project,
        href: `/${project.owner}/${project.repo}?type=${project.repo_type}&language=${project.language}`,
        formattedDate: dateFormatter.format(new Date(project.submittedAt)),
      };
    });
  }, [filteredProjects, dateFormatter]);

  const clearSearch = () => {
    setSearchQuery('');
  };

  const handleDelete = async (project: ProcessedProject) => {
    if (!confirm(`Are you sure you want to delete project ${project.name}?`)) {
      return;
    }
    try {
      const response = await fetch('/api/wiki/projects', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          owner: project.owner,
          repo: project.repo,
          repo_type: project.repo_type,
          language: project.language,
        }),
      });
      if (!response.ok) {
        const errorBody = await response.json().catch(() => ({ error: response.statusText }));
        throw new Error(errorBody.error || response.statusText);
      }
      setProjects(prev => prev.filter(p => p.id !== project.id));
    } catch (e: unknown) {
      console.error('Failed to delete project:', e);
      alert(`Failed to delete project: ${e instanceof Error ? e.message : 'Unknown error'}`);
    }
  };

  return (
    <div className={`${className}`}>
      {showHeader && (
        <header className="mb-6">
          <div className="flex items-center justify-between">
            <h1 className="text-3xl font-bold text-[var(--accent-primary)]">{t('title')}</h1>
            <Link href="/" className="text-[var(--accent-primary)] hover:underline">
              {t('backToHome')}
            </Link>
          </div>
        </header>
      )}

      {/* Search Bar and View Toggle */}
      <div className="mb-6 flex flex-col sm:flex-row gap-4">
        {/* Search Bar */}
        <div className="relative flex-1">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t('searchPlaceholder')}
            className="input-japanese block w-full pl-4 pr-12 py-2.5 border border-[var(--border-color)] rounded-lg bg-[var(--background)] text-[var(--foreground)] placeholder:text-[var(--muted)] focus:outline-none focus:border-[var(--accent-primary)] focus:ring-1 focus:ring-[var(--accent-primary)]"
          />
          {searchQuery && (
            <button
              onClick={clearSearch}
              className="absolute inset-y-0 right-0 flex items-center pr-3 text-[var(--muted)] hover:text-[var(--foreground)] transition-colors"
            >
              <FaTimes className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* View Toggle */}
        <div className="flex items-center bg-[var(--background)] border border-[var(--border-color)] rounded-lg p-1">
          <button
            onClick={() => setViewMode('card')}
            className={`p-2 rounded transition-colors ${
              viewMode === 'card'
                ? 'bg-[var(--accent-primary)] text-white'
                : 'text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--card-bg)]'
            }`}
            title="Card View"
          >
            <FaTh className="h-4 w-4" />
          </button>
          <button
            onClick={() => setViewMode('list')}
            className={`p-2 rounded transition-colors ${
              viewMode === 'list'
                ? 'bg-[var(--accent-primary)] text-white'
                : 'text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--card-bg)]'
            }`}
            title="List View"
          >
            <FaList className="h-4 w-4" />
          </button>
        </div>
      </div>

      {isLoading && <p className="text-[var(--muted)]">{t('loadingProjects')}</p>}
      {error && <p className="text-[var(--highlight)]">{t('errorLoading')} {error}</p>}

      {!isLoading && !error && preparedProjects.length > 0 && (
        <div className={viewMode === 'card' ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4' : 'space-y-2'}>
            {preparedProjects.map((project) => (
            viewMode === 'card' ? (
              <div key={project.id} className="relative p-4 border border-[var(--border-color)] rounded-lg bg-[var(--card-bg)] shadow-sm hover:shadow-md transition-all duration-200 hover:scale-[1.02]">
                <button
                  type="button"
                  onClick={() => handleDelete(project)}
                  className="absolute top-2 right-2 text-[var(--muted)] hover:text-[var(--foreground)]"
                  title="Delete project"
                >
                  <FaTimes className="h-4 w-4" />
                </button>
                <Link
                  href={project.href}
                  className="block"
                >
                  <h3 className="text-lg font-semibold text-[var(--link-color)] hover:underline mb-2 line-clamp-2">
                    {project.name}
                  </h3>
                  <div className="flex flex-wrap gap-2 mb-3">
                    <span className="px-2 py-1 text-xs bg-[var(--accent-primary)]/10 text-[var(--accent-primary)] rounded-full border border-[var(--accent-primary)]/20">
                      {project.repo_type}
                    </span>
                    <span className="px-2 py-1 text-xs bg-[var(--background)] text-[var(--muted)] rounded-full border border-[var(--border-color)]">
                      {project.language}
                    </span>
                  </div>
                  <p className="text-xs text-[var(--muted)]">
                    {t('processedOn')} {project.formattedDate}
                  </p>
                </Link>
              </div>
            ) : (
              <div key={project.id} className="relative p-3 border border-[var(--border-color)] rounded-lg bg-[var(--card-bg)] hover:bg-[var(--background)] transition-colors">
                <button
                  type="button"
                  onClick={() => handleDelete(project)}
                  className="absolute top-2 right-2 text-[var(--muted)] hover:text-[var(--foreground)]"
                  title="Delete project"
                >
                  <FaTimes className="h-4 w-4" />
                </button>
                <Link
                  href={project.href}
                  className="flex items-center justify-between"
                >
                  <div className="flex-1 min-w-0">
                    <h3 className="text-base font-medium text-[var(--link-color)] hover:underline truncate">
                      {project.name}
                    </h3>
                    <p className="text-xs text-[var(--muted)] mt-1">
                      {t('processedOn')} {project.formattedDate} • {project.repo_type} • {project.language}
                    </p>
                  </div>
                  <div className="flex gap-2 ml-4">
                    <span className="px-2 py-1 text-xs bg-[var(--accent-primary)]/10 text-[var(--accent-primary)] rounded border border-[var(--accent-primary)]/20">
                      {project.repo_type}
                    </span>
                  </div>
                </Link>
              </div>
            )
          ))}
        </div>
      )}

      {!isLoading && !error && projects.length > 0 && filteredProjects.length === 0 && searchQuery && (
        <p className="text-[var(--muted)]">{t('noSearchResults')}</p>
      )}

      {!isLoading && !error && projects.length === 0 && (
        <p className="text-[var(--muted)]">{t('noProjects')}</p>
      )}
    </div>
  );
}

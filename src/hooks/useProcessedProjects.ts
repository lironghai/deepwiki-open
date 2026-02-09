import { useState, useEffect } from 'react';

import type { ProcessedProject } from '@/types/processedProject';

export function useProcessedProjects() {
  const [projects, setProjects] = useState<ProcessedProject[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    const fetchProjects = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await fetch('/api/wiki/projects', { signal: controller.signal });
        if (!response.ok) {
          throw new Error(`Failed to fetch projects: ${response.statusText}`);
        }
        const data = await response.json();
        if (data.error) {
          throw new Error(data.error);
        }
        setProjects(data as ProcessedProject[]);
      } catch (e: unknown) {
        if (e instanceof DOMException && e.name === 'AbortError') {
          return;
        }
        console.error('Failed to load projects from API:', e);
        const message = e instanceof Error ? e.message : "An unknown error occurred.";
        setError(message);
        setProjects([]);
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    };

    fetchProjects();
    return () => {
      controller.abort();
    };
  }, []);

  return { projects, setProjects, isLoading, error };
}

'use client';

import React from 'react';
import ProcessedProjects from '@/components/ProcessedProjects';
import { useLanguage } from '@/contexts/LanguageContext';
import { useProcessedProjects } from '@/hooks/useProcessedProjects';

export default function WikiProjectsPage() {
  const { messages } = useLanguage();
  const {
    projects,
    setProjects,
    isLoading,
    error,
  } = useProcessedProjects();

  return (
    <div className="container mx-auto p-4">
      <ProcessedProjects
        showHeader={true}
        messages={messages}
        className=""
        projects={projects}
        setProjects={setProjects}
        isLoading={isLoading}
        error={error}
      />
    </div>
  );
}

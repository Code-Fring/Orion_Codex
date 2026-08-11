'use client';

import { useState } from 'react';

export default function HomePage() {
  const [prompt, setPrompt] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;

    setIsGenerating(true);
    try {
      const response = await fetch('/api/v1/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: 'New Project', prompt }),
      });
      const data = await response.json();
      if (response.ok) {
        window.location.href = `/projects/${data.id}`;
      }
    } catch (error) {
      console.error('Failed to create project:', error);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-8 bg-gray-50 dark:bg-gray-900">
      <div className="max-w-2xl w-full">
        <h1 className="text-4xl font-bold text-center mb-8 text-gray-900 dark:text-white">
          {project_name}
        </h1>
        <p className="text-center text-gray-600 dark:text-gray-400 mb-8">
          {description}
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="prompt" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Describe what you want to build
            </label>
            <textarea
              id="prompt"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              rows={6}
              className="w-full p-4 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="e.g., Build a task management app with user authentication, project boards, and real-time collaboration..."
              required
            />
          </div>
          <button
            type="submit"
            disabled={isGenerating || !prompt.trim()}
            className="w-full py-3 px-4 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isGenerating ? 'Generating...' : 'Generate Project'}
          </button>
        </form>
      </div>
    </main>
  );
}
'use client';

import { useState } from 'react';
import { Sidebar, ChatInterface, DocumentsPanel, SettingsPanel, AgentDashboard, CompliancePanel } from '@/components';

export default function Home() {
  const [activeTab, setActiveTab] = useState<'chat' | 'agents' | 'compliance' | 'documents' | 'settings'>('chat');

  return (
    <div className="flex h-screen bg-zinc-950">
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />
      <main className="flex-1 flex flex-col bg-zinc-900">
        {activeTab === 'chat' && <ChatInterface />}
        {activeTab === 'agents' && <AgentDashboard />}
        {activeTab === 'compliance' && <CompliancePanel />}
        {activeTab === 'documents' && <DocumentsPanel />}
        {activeTab === 'settings' && <SettingsPanel />}
      </main>
    </div>
  );
}


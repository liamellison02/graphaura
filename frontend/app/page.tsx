'use client';

import dynamic from 'next/dynamic';
import { Suspense, useEffect } from 'react';
import { useGraphStore } from '@/stores/graphStore';
import { graphApi } from '@/lib/api';

const Graph3D = dynamic(() => import('@/components/Graph3D'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-screen bg-gray-900">
      <div className="text-white text-xl">loading 3d graph...</div>
    </div>
  ),
});

export default function Home() {
  const { searchQuery, setSearchQuery, filterByType, setFilterByType, setGraphData, setLoading, setError, isLoading } = useGraphStore();

  useEffect(() => {
    const loadGraphData = async () => {
      setLoading(true);
      try {
        const data = await graphApi.getGraph();
        setGraphData(data);
        console.log('loaded graph data:', data.nodes.length, 'nodes,', data.links.length, 'links');
      } catch (error) {
        console.error('failed to load graph data:', error);
        setError('failed to load graph data');
      } finally {
        setLoading(false);
      }
    };

    loadGraphData();
  }, [setGraphData, setLoading, setError]);

  return (
    <div className="relative w-screen h-screen bg-[#000011] overflow-hidden">
      {/* Bottom Search Controls */}
      <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 z-10 bg-gray-800/50 backdrop-blur-sm rounded-lg px-6 py-2 shadow-xl w-11/12 max-w-4xl">
        <div className="flex items-center gap-4">
          {/* Search */}
          <input
            type="text"
            placeholder="search nodes..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="flex-1 px-3 py-1.5 bg-gray-700/60 text-white rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 placeholder-gray-400"
          />

          {/* Filter by Type */}
          <div className="flex gap-2">
            <button
              onClick={() => setFilterByType(null)}
              className={`px-3 py-1 rounded-lg transition-colors text-sm ${
                !filterByType ? 'bg-blue-600 text-white' : 'bg-gray-700/60 text-gray-300 hover:bg-gray-600/60'
              }`}
            >
              all
            </button>
            <button
              onClick={() => setFilterByType('person')}
              className={`px-3 py-1 rounded-lg transition-colors text-sm ${
                filterByType === 'person' ? 'bg-blue-600 text-white' : 'bg-gray-700/60 text-gray-300 hover:bg-gray-600/60'
              }`}
            >
              people
            </button>
            <button
              onClick={() => setFilterByType('event')}
              className={`px-3 py-1 rounded-lg transition-colors text-sm ${
                filterByType === 'event' ? 'bg-green-600 text-white' : 'bg-gray-700/60 text-gray-300 hover:bg-gray-600/60'
              }`}
            >
              events
            </button>
            <button
              onClick={() => setFilterByType('location')}
              className={`px-3 py-1 rounded-lg transition-colors text-sm ${
                filterByType === 'location' ? 'bg-red-600 text-white' : 'bg-gray-700/60 text-gray-300 hover:bg-gray-600/60'
              }`}
            >
              locations
            </button>
          </div>
        </div>
      </div>

      {/* Header - Just the title */}
      <div className="absolute top-4 left-4 z-10">
        <h1 className="text-2xl font-bold text-white">graphaura</h1>
      </div>

      {/* Selected Node Info */}
      <SelectedNodeInfo />

      {/* 3D Graph */}
      {isLoading ? (
        <div className="flex items-center justify-center h-screen bg-gray-900">
          <div className="text-white text-xl">fetching graph data...</div>
        </div>
      ) : (
        <Suspense fallback={
          <div className="flex items-center justify-center h-screen bg-gray-900">
            <div className="text-white text-xl">loading 3d graph...</div>
          </div>
        }>
          <Graph3D backgroundColor="#000011" />
        </Suspense>
      )}
    </div>
  );
}

function SelectedNodeInfo() {
  const { selectedNode } = useGraphStore();

  if (!selectedNode) return null;

  return (
    <div className="absolute top-4 right-4 z-10 bg-gray-800/70 backdrop-blur-sm rounded-lg p-4 shadow-xl max-w-sm">
      <h3 className="text-lg font-semibold text-white mb-2">{selectedNode.name}</h3>
      <p className="text-sm text-gray-300 capitalize mb-2">type: {selectedNode.type}</p>
      {selectedNode.metadata && (
        <div className="text-sm text-gray-400">
          {Object.entries(selectedNode.metadata).map(([key, value]) => (
            <div key={key} className="mb-1">
              <span className="capitalize">{key}: </span>
              <span>{String(value)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
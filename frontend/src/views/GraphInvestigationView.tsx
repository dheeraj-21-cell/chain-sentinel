import React, { useState, useEffect, useRef, useCallback } from 'react';
import cytoscape, { Core, NodeSingular, EventObject } from 'cytoscape';
import {
  GraphSummaryResponse,
  GraphElementNode,
  GraphElementEdge,
  GraphElementsResponse,
  getGraphElements,
  expandGraphNeighborhood,
  WalletActivity,
  CorrelationRecord,
  RiskFinding,
  BehavioralFinding,
  AnomalyScoreItem,
  WalletClusterItem,
  WalletGraphMetrics,
  NetworkObservation,
} from '../services/api';
import { EntityInvestigationSummary } from '../components/EntityInvestigationSummary';
import { useI18n } from '../services/i18n';

interface GraphInvestigationViewProps {
  datasetId: string;
  graphSummary: GraphSummaryResponse | null;
  onRefreshGraph: () => Promise<void>;
  onSelectEntity: (type: 'wallet' | 'transaction' | 'ip', id: string) => void;
  initialCenterNode?: string | null;
  wallets?: WalletActivity[];
  correlations?: CorrelationRecord[];
  riskFindings?: RiskFinding[];
  behaviorFindings?: BehavioralFinding[];
  anomalies?: AnomalyScoreItem[];
  clusters?: WalletClusterItem[];
  graphMetrics?: WalletGraphMetrics[];
  networkObservations?: NetworkObservation[];
}

type LayoutType = 'topology' | 'cose';
type NodeFilterType = 'all' | 'wallet' | 'transaction' | 'ip' | 'infra';

export const GraphInvestigationView: React.FC<GraphInvestigationViewProps> = ({
  datasetId,
  graphSummary: _graphSummary,
  onSelectEntity,
  initialCenterNode,
  wallets = [],
  correlations = [],
  riskFindings = [],
  behaviorFindings = [],
  anomalies = [],
  clusters = [],
  graphMetrics = [],
  networkObservations = [],
}) => {
  const { t } = useI18n();

  // Cytoscape Canvas References
  const cyContainerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);

  // Graph Data & State
  const [elementsData, setElementsData] = useState<GraphElementsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Search
  const [searchQuery, setSearchQuery] = useState(initialCenterNode || '');

  // Selected Entity Inspector (Desktop right drawer, mobile bottom sheet)
  const [selectedNode, setSelectedNode] = useState<GraphElementNode | null>(null);
  const [showLegend, setShowLegend] = useState(false);
  const [layoutMode, setLayoutMode] = useState<LayoutType>('topology');
  const [activeFilter, setActiveFilter] = useState<NodeFilterType>('all');

  useEffect(() => {
    (window as any).__setSelectedNode = setSelectedNode;
  }, []);

  // Cytoscape Stylesheet matching exact real node types
  const stylesheet: cytoscape.StylesheetStyle[] = [
    {
      selector: 'node',
      style: {
        'label': 'data(label)',
        'font-size': '10px',
        'color': '#f8fafc',
        'text-valign': 'bottom',
        'text-margin-y': 6,
        'text-background-color': '#090d16',
        'text-background-opacity': 0.85,
        'text-background-padding': '3px',
        'text-background-shape': 'roundrectangle',
        'transition-property': 'background-color, border-color, width, height, opacity',
        'transition-duration': 200,
      },
    },
    // Wallet Node (○ W: Blue Circle / Ellipse)
    {
      selector: 'node[type = "wallet"]',
      style: {
        'background-color': '#0284c7',
        'border-color': '#38bdf8',
        'border-width': 2.5,
        'shape': 'ellipse',
        'width': 34,
        'height': 34,
      },
    },
    // Transaction Node (◇ TX: Cyan Diamond)
    {
      selector: 'node[type = "transaction"]',
      style: {
        'background-color': '#0891b2',
        'border-color': '#22d3ee',
        'border-width': 2.5,
        'shape': 'diamond',
        'width': 32,
        'height': 32,
      },
    },
    // Observed IP Node (⬡ IP: Indigo Hexagon)
    {
      selector: 'node[type = "ip"]',
      style: {
        'background-color': '#4f46e5',
        'border-color': '#818cf8',
        'border-width': 2.5,
        'shape': 'hexagon',
        'width': 32,
        'height': 32,
      },
    },
    // ASN Node (△ ASN: Amber Triangle)
    {
      selector: 'node[type = "asn"]',
      style: {
        'background-color': '#d97706',
        'border-color': '#fbbf24',
        'border-width': 2,
        'shape': 'triangle',
        'width': 28,
        'height': 28,
      },
    },
    // Country Node (▢ CC: Purple Round-Rectangle)
    {
      selector: 'node[type = "country"]',
      style: {
        'background-color': '#7e22ce',
        'border-color': '#c084fc',
        'border-width': 2,
        'shape': 'round-rectangle',
        'width': 28,
        'height': 28,
      },
    },
    // Risk Highlights
    {
      selector: 'node[risk_priority = "CRITICAL"]',
      style: {
        'border-color': '#ef4444',
        'border-width': 4.5,
        'underlay-color': '#ef4444',
        'underlay-padding': 4,
        'underlay-opacity': 0.35,
      },
    },
    {
      selector: 'node[risk_priority = "HIGH"]',
      style: {
        'border-color': '#f59e0b',
        'border-width': 3.5,
      },
    },
    // Selected Node State
    {
      selector: 'node:selected',
      style: {
        'border-color': '#ffffff',
        'border-width': 4,
        'underlay-color': '#38bdf8',
        'underlay-padding': 6,
        'underlay-opacity': 0.5,
      },
    },
    // Directed Edges
    {
      selector: 'edge',
      style: {
        'curve-style': 'bezier',
        'target-arrow-shape': 'triangle',
        'arrow-scale': 1.1,
        'width': 1.8,
        'line-color': '#475569',
        'target-arrow-color': '#475569',
        'opacity': 0.7,
        'transition-property': 'opacity, width, line-color',
        'transition-duration': 200,
      },
    },
    {
      selector: 'edge[type = "HAS_INPUT"]',
      style: {
        'line-color': '#38bdf8',
        'target-arrow-color': '#38bdf8',
        'width': 2,
      },
    },
    {
      selector: 'edge[type = "HAS_OUTPUT"]',
      style: {
        'line-color': '#10b981',
        'target-arrow-color': '#10b981',
        'width': 2,
      },
    },
    {
      selector: 'edge[type = "OBSERVED_TRANSACTION"], edge[type = "OBSERVED_AT"]',
      style: {
        'line-color': '#a855f7',
        'target-arrow-color': '#a855f7',
        'line-style': 'dashed',
        'width': 1.6,
      },
    },
    {
      selector: 'edge[type = "LOCATED_IN"]',
      style: {
        'line-color': '#c084fc',
        'target-arrow-color': '#c084fc',
        'width': 1.4,
      },
    },
    {
      selector: 'edge[type = "BELONGS_TO"]',
      style: {
        'line-color': '#fbbf24',
        'target-arrow-color': '#fbbf24',
        'width': 1.4,
      },
    },
    {
      selector: 'edge:selected',
      style: {
        'width': 3.5,
        'line-color': '#ffffff',
        'target-arrow-color': '#ffffff',
        'opacity': 1,
      },
    },
    // Focused Sub-Graph Highlighting & Dimming
    {
      selector: '.dimmed',
      style: {
        'opacity': 0.18,
      },
    },
    {
      selector: '.highlighted',
      style: {
        'opacity': 1,
        'z-index': 999,
      },
    },
    {
      selector: '.filter-hidden',
      style: {
        'display': 'none',
      },
    },
  ];

  // Truncate node label for readability
  const formatLabel = (canonicalId: string, label: string): string => {
    if (label === 'Country') return canonicalId;
    if (label === 'ASN') return `AS${canonicalId}`;
    if (canonicalId.length > 12) {
      return `${canonicalId.slice(0, 5)}...${canonicalId.slice(-4)}`;
    }
    return canonicalId;
  };

  // --------------------------------------------------------------------------
  // LAYOUT ENGINE: TOPOLOGY FLOW (Hierarchical Downward Flow)
  // Wallet -> Transaction -> Observed IP -> Country / ASN
  // --------------------------------------------------------------------------
  const applyTopologyLayout = useCallback((cy: Core) => {
    const allNodes = cy.nodes();
    if (allNodes.length === 0) return;

    // Separate nodes into distinct topological layers
    const walletNodes = allNodes.filter('[type = "wallet"]');
    const txNodes = allNodes.filter('[type = "transaction"]');
    const ipNodes = allNodes.filter('[type = "ip"]');
    const infraNodes = allNodes.filter('[type = "country"], [type = "asn"]');

    const tierY = {
      wallet: 80,
      transaction: 260,
      ip: 440,
      infra: 620,
    };

    const minSpacing = 150; // Ample spacing to prevent label overlap

    const layoutTier = (tierCollection: cytoscape.NodeCollection, y: number) => {
      const count = tierCollection.length;
      if (count === 0) return;
      const totalWidth = (count - 1) * minSpacing;
      const startX = -totalWidth / 2;

      tierCollection.forEach((node, idx) => {
        node.position({
          x: startX + idx * minSpacing,
          y,
        });
      });
    };

    cy.batch(() => {
      layoutTier(walletNodes, tierY.wallet);
      layoutTier(txNodes, tierY.transaction);
      layoutTier(ipNodes, tierY.ip);
      layoutTier(infraNodes, tierY.infra);
    });

    cy.fit(undefined, 60);
  }, []);

  // --------------------------------------------------------------------------
  // LAYOUT ENGINE: FORCE-DIRECTED (COSE with strong repulsion)
  // --------------------------------------------------------------------------
  const applyCoseLayout = useCallback((cy: Core) => {
    cy.layout({
      name: 'cose',
      animate: true,
      animationDuration: 600,
      randomize: false,
      nodeRepulsion: () => 450000,
      idealEdgeLength: () => 110,
      edgeElasticity: () => 32,
      gravity: 0.05,
      padding: 50,
    }).run();
  }, []);

  // Run the current layout mode
  const runLayout = useCallback(
    (mode: LayoutType, cy?: Core | null) => {
      const targetCy = cy || cyRef.current;
      if (!targetCy) return;
      if (mode === 'topology') {
        applyTopologyLayout(targetCy);
      } else {
        applyCoseLayout(targetCy);
      }
    },
    [applyTopologyLayout, applyCoseLayout]
  );

  // Load Graph Elements from Backend
  const fetchGraph = useCallback(
    async (centerNode?: string) => {
      setLoading(true);
      setErrorMsg(null);
      try {
        const data = await getGraphElements(datasetId, 100, centerNode);
        setElementsData(data);
        setSelectedNode(null);
      } catch (err: unknown) {
        if (err instanceof Error) {
          setErrorMsg(err.message);
        } else {
          setErrorMsg('Failed to load graph data.');
        }
      } finally {
        setLoading(false);
      }
    },
    [datasetId]
  );

  // Resize cytoscape with ResizeObserver for responsiveness
  useEffect(() => {
    if (!cyContainerRef.current) return;
    const observer = new ResizeObserver(() => {
      if (cyRef.current) {
        cyRef.current.resize();
      }
    });
    observer.observe(cyContainerRef.current);
    return () => observer.disconnect();
  }, []);

  // Resize when selected node drawer opens or closes
  useEffect(() => {
    if (cyRef.current) {
      const timer = setTimeout(() => {
        cyRef.current?.resize();
      }, 60);
      return () => clearTimeout(timer);
    }
  }, [selectedNode]);

  // Initial Load
  useEffect(() => {
    fetchGraph(initialCenterNode || undefined);
  }, [fetchGraph, initialCenterNode]);

  // Mount Cytoscape Canvas
  useEffect(() => {
    if (!cyContainerRef.current || !elementsData) return;

    if (!cyRef.current) {
      cyRef.current = cytoscape({
        container: cyContainerRef.current,
        style: stylesheet,
        minZoom: 0.1,
        maxZoom: 3.0,
        wheelSensitivity: 0.25,
      });

      (window as any).__cy = cyRef.current;

      // Node selection listener: highlights neighborhood and dims non-connected
      const handleNodeSelect = (target: NodeSingular) => {
        if (!target) return;
        const cy = cyRef.current;
        if (cy) {
          const neighborhood = target.neighborhood().add(target);
          cy.elements().removeClass('highlighted').addClass('dimmed');
          neighborhood.removeClass('dimmed').addClass('highlighted');
        }
        const nodeData = target.data() as GraphElementNode & { full_id: string; raw_node: GraphElementNode };
        if (nodeData?.raw_node) {
          setSelectedNode(nodeData.raw_node);
        }
      };

      cyRef.current.on('tap', 'node', (evt: EventObject) => {
        handleNodeSelect(evt.target as NodeSingular);
      });

      cyRef.current.on('select', 'node', (evt: EventObject) => {
        handleNodeSelect(evt.target as NodeSingular);
      });

      // Background tap clears selection and restores opacity
      cyRef.current.on('tap', (evt: EventObject) => {
        if (evt.target === cyRef.current) {
          cyRef.current?.elements().removeClass('dimmed').removeClass('highlighted');
          setSelectedNode(null);
        }
      });
    }

    const cy = cyRef.current;
    cy.elements().remove();

    const cytoscapeNodes = elementsData.nodes.map((n) => ({
      group: 'nodes' as const,
      data: {
        id: n.id,
        label: formatLabel(n.canonical_id, n.label),
        full_id: n.canonical_id,
        type: n.label.toLowerCase(),
        risk_priority: n.risk_priority || 'NONE',
        risk_score: n.risk_score || 0,
        is_anomaly: n.ml_anomaly?.is_anomaly || false,
        raw_node: n,
      },
    }));

    const cytoscapeEdges = elementsData.edges.map((e: GraphElementEdge) => ({
      group: 'edges' as const,
      data: {
        id: e.id,
        source: e.source,
        target: e.target,
        type: e.type,
      },
    }));

    cy.add([...cytoscapeNodes, ...cytoscapeEdges]);

    // Apply default layout (Topology Flow)
    runLayout(layoutMode, cy);

    // If center node requested, select it
    if (initialCenterNode) {
      const match = cy.nodes().filter((n) => n.data('full_id') === initialCenterNode);
      if (match.length > 0) {
        match.select();
        cy.center(match);
      }
    }
  }, [elementsData, stylesheet, initialCenterNode, layoutMode, runLayout]);

  // Handle layout mode toggle
  const handleToggleLayout = (newMode: LayoutType) => {
    setLayoutMode(newMode);
    runLayout(newMode);
  };

  // Node Type Filtering
  const handleFilterChange = (filter: NodeFilterType) => {
    setActiveFilter(filter);
    const cy = cyRef.current;
    if (!cy) return;

    if (filter === 'all') {
      cy.elements().removeClass('filter-hidden');
    } else if (filter === 'infra') {
      cy.nodes().forEach((n) => {
        const type = n.data('type');
        if (type === 'country' || type === 'asn') {
          n.removeClass('filter-hidden');
        } else {
          n.addClass('filter-hidden');
        }
      });
      cy.edges().forEach((e) => {
        if (e.source().hasClass('filter-hidden') || e.target().hasClass('filter-hidden')) {
          e.addClass('filter-hidden');
        } else {
          e.removeClass('filter-hidden');
        }
      });
    } else {
      cy.nodes().forEach((n) => {
        if (n.data('type') === filter) {
          n.removeClass('filter-hidden');
        } else {
          n.addClass('filter-hidden');
        }
      });
      cy.edges().forEach((e) => {
        if (e.source().hasClass('filter-hidden') || e.target().hasClass('filter-hidden')) {
          e.addClass('filter-hidden');
        } else {
          e.removeClass('filter-hidden');
        }
      });
    }

    const visibleElements = cy.elements(':visible');
    if (visibleElements.length > 0) {
      cy.fit(visibleElements, 40);
    }
  };

  // Search Handler
  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) {
      fetchGraph();
      return;
    }

    const query = searchQuery.trim();
    if (cyRef.current) {
      const existing = cyRef.current.nodes().filter(
        (n) => n.data('full_id').toLowerCase().includes(query.toLowerCase())
      );
      if (existing.length > 0) {
        existing.select();
        cyRef.current.animate({
          center: { eles: existing },
          zoom: 1.0,
          duration: 400,
        });
        const raw = existing.data('raw_node') as GraphElementNode;
        if (raw) setSelectedNode(raw);
        return;
      }
    }

    await fetchGraph(query);
  };

  // Zoom / Fit Helpers
  const handleZoomIn = () => {
    if (cyRef.current) {
      cyRef.current.zoom({
        level: cyRef.current.zoom() * 1.3,
        renderedPosition: { x: cyRef.current.width() / 2, y: cyRef.current.height() / 2 },
      });
    }
  };

  const handleZoomOut = () => {
    if (cyRef.current) {
      cyRef.current.zoom({
        level: cyRef.current.zoom() * 0.75,
        renderedPosition: { x: cyRef.current.width() / 2, y: cyRef.current.height() / 2 },
      });
    }
  };

  const handleFit = () => {
    if (cyRef.current) {
      const visible = cyRef.current.elements(':visible');
      cyRef.current.fit(visible.length > 0 ? visible : undefined, 45);
    }
  };

  const handleReset = () => {
    setSearchQuery('');
    setSelectedNode(null);
    setActiveFilter('all');
    if (cyRef.current) {
      cyRef.current.elements().removeClass('dimmed').removeClass('highlighted').removeClass('filter-hidden');
    }
    fetchGraph();
  };

  // Expand neighborhood for selected node
  const handleExpandNeighbors = async (nodeId: string) => {
    try {
      const expansion = await expandGraphNeighborhood(datasetId, nodeId);
      if (cyRef.current && expansion.nodes.length > 0) {
        const currentIds = new Set(cyRef.current.nodes().map((n) => n.id()));
        const newNodes = expansion.nodes
          .filter((n) => !currentIds.has(n.id))
          .map((n) => ({
            group: 'nodes' as const,
            data: {
              id: n.id,
              label: formatLabel(n.canonical_id, n.label),
              full_id: n.canonical_id,
              type: n.label.toLowerCase(),
              risk_priority: n.risk_priority || 'NONE',
              risk_score: n.risk_score || 0,
              is_anomaly: n.ml_anomaly?.is_anomaly || false,
              raw_node: n,
            },
          }));

        const currentEdgeIds = new Set(cyRef.current.edges().map((e) => e.id()));
        const newEdges = expansion.edges
          .filter((e) => !currentEdgeIds.has(e.id))
          .map((e: GraphElementEdge) => ({
            group: 'edges' as const,
            data: {
              id: e.id,
              source: e.source,
              target: e.target,
              type: e.type,
            },
          }));

        cyRef.current.add([...newNodes, ...newEdges]);
        runLayout(layoutMode);
      }
    } catch {
      // expand failed
    }
  };

  // Node count per type
  const nodeCounts = {
    total: elementsData?.nodes.length || 0,
    wallets: elementsData?.nodes.filter((n) => n.label.toLowerCase() === 'wallet').length || 0,
    transactions: elementsData?.nodes.filter((n) => n.label.toLowerCase() === 'transaction').length || 0,
    ips: elementsData?.nodes.filter((n) => n.label.toLowerCase() === 'ip').length || 0,
    infra: elementsData?.nodes.filter((n) => ['country', 'asn'].includes(n.label.toLowerCase())).length || 0,
  };

  return (
    <div>
      {/* Header */}
      <div className="view-header">
        <div>
          <h1 className="view-title">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--cyber-purple)" strokeWidth="2.2">
              <circle cx="6" cy="6" r="3"></circle>
              <circle cx="18" cy="18" r="3"></circle>
              <circle cx="18" cy="6" r="3"></circle>
              <line x1="8.5" y1="7.5" x2="15.5" y2="16.5"></line>
              <line x1="9" y1="6" x2="15" y2="6"></line>
            </svg>
            {t('graph_title')}
          </h1>
          <p className="view-subtitle">{t('graph_subtitle')}</p>
        </div>

        {/* Search Bar & Primary Actions */}
        <form onSubmit={handleSearch} style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <input
            type="text"
            placeholder={t('graph_search_placeholder')}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{ minWidth: '240px' }}
          />
          <button type="submit" className="btn-primary" style={{ padding: '0.4rem 0.8rem' }}>
            {t('graph_search_btn')}
          </button>
          <button type="button" className="btn-secondary" onClick={handleReset} title="Reset graph view">
            {t('graph_reset_btn')}
          </button>
        </form>
      </div>

      {/* Sub-Header Toolbar: Layout Switcher, Filter Pills, Legend Toggle */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '0.5rem',
          marginBottom: '0.75rem',
          padding: '0.5rem 0.75rem',
          background: 'var(--bg-elevated)',
          border: '1px solid var(--border-medium)',
          borderRadius: '8px',
        }}
      >
        {/* Filter Pills */}
        <div style={{ display: 'flex', gap: '0.35rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600, marginRight: '0.2rem' }}>
            VIEW:
          </span>
          <button
            className={`btn-ghost ${activeFilter === 'all' ? 'active' : ''}`}
            onClick={() => handleFilterChange('all')}
            style={{
              padding: '0.25rem 0.6rem',
              fontSize: '0.72rem',
              background: activeFilter === 'all' ? 'rgba(56, 189, 248, 0.15)' : undefined,
              borderColor: activeFilter === 'all' ? 'var(--cyber-blue)' : undefined,
            }}
          >
            All ({nodeCounts.total})
          </button>
          <button
            className={`btn-ghost ${activeFilter === 'wallet' ? 'active' : ''}`}
            onClick={() => handleFilterChange('wallet')}
            style={{
              padding: '0.25rem 0.6rem',
              fontSize: '0.72rem',
              background: activeFilter === 'wallet' ? 'rgba(2, 132, 199, 0.2)' : undefined,
              borderColor: activeFilter === 'wallet' ? '#0284c7' : undefined,
            }}
          >
            ○ Wallets ({nodeCounts.wallets})
          </button>
          <button
            className={`btn-ghost ${activeFilter === 'transaction' ? 'active' : ''}`}
            onClick={() => handleFilterChange('transaction')}
            style={{
              padding: '0.25rem 0.6rem',
              fontSize: '0.72rem',
              background: activeFilter === 'transaction' ? 'rgba(8, 145, 178, 0.2)' : undefined,
              borderColor: activeFilter === 'transaction' ? '#0891b2' : undefined,
            }}
          >
            ◇ Transactions ({nodeCounts.transactions})
          </button>
          <button
            className={`btn-ghost ${activeFilter === 'ip' ? 'active' : ''}`}
            onClick={() => handleFilterChange('ip')}
            style={{
              padding: '0.25rem 0.6rem',
              fontSize: '0.72rem',
              background: activeFilter === 'ip' ? 'rgba(79, 70, 229, 0.2)' : undefined,
              borderColor: activeFilter === 'ip' ? '#4f46e5' : undefined,
            }}
          >
            ⬡ IPs ({nodeCounts.ips})
          </button>
          <button
            className={`btn-ghost ${activeFilter === 'infra' ? 'active' : ''}`}
            onClick={() => handleFilterChange('infra')}
            style={{
              padding: '0.25rem 0.6rem',
              fontSize: '0.72rem',
              background: activeFilter === 'infra' ? 'rgba(126, 34, 206, 0.2)' : undefined,
              borderColor: activeFilter === 'infra' ? '#7e22ce' : undefined,
            }}
          >
            Infrastructure ({nodeCounts.infra})
          </button>
        </div>

        {/* Layout Switcher & Legend Toggle */}
        <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
          <div
            style={{
              display: 'flex',
              background: 'var(--bg-darkest)',
              borderRadius: '6px',
              border: '1px solid var(--border-subtle)',
              padding: '2px',
            }}
          >
            <button
              onClick={() => handleToggleLayout('topology')}
              style={{
                border: 'none',
                background: layoutMode === 'topology' ? 'var(--cyber-blue)' : 'transparent',
                color: layoutMode === 'topology' ? '#000' : 'var(--text-secondary)',
                fontWeight: 600,
                fontSize: '0.72rem',
                padding: '0.25rem 0.55rem',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
              title="Topology Flow (Hierarchical Top-Down)"
            >
              ↓ Topology Flow
            </button>
            <button
              onClick={() => handleToggleLayout('cose')}
              style={{
                border: 'none',
                background: layoutMode === 'cose' ? 'var(--cyber-blue)' : 'transparent',
                color: layoutMode === 'cose' ? '#000' : 'var(--text-secondary)',
                fontWeight: 600,
                fontSize: '0.72rem',
                padding: '0.25rem 0.55rem',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
              title="Force-Directed (Organic Cluster Spread)"
            >
              ☊ Force-Directed
            </button>
          </div>

          <button
            className="btn-ghost"
            onClick={() => setShowLegend((p) => !p)}
            style={{
              fontSize: '0.74rem',
              padding: '0.3rem 0.6rem',
              color: showLegend ? 'var(--cyber-blue)' : undefined,
              borderColor: showLegend ? 'var(--cyber-blue)' : undefined,
            }}
          >
            ℹ Graph Legend
          </button>
        </div>
      </div>

      {/* Main Canvas & Details Panel Layout */}
      <div
        style={{
          position: 'relative',
          height: 'calc(100vh - 250px)',
          minHeight: '520px',
          background: 'var(--bg-darkest)',
          border: '1px solid var(--border-medium)',
          borderRadius: '10px',
          overflow: 'hidden',
          display: 'flex',
        }}
      >
        {/* Cytoscape Canvas */}
        <div
          ref={cyContainerRef}
          style={{
            flex: 1,
            minWidth: 0,
            height: '100%',
            position: 'relative',
          }}
        />

        {/* Floating Zoom & Controls Toolbar */}
        <div
          style={{
            position: 'absolute',
            bottom: '16px',
            left: '16px',
            display: 'flex',
            gap: '0.35rem',
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-medium)',
            padding: '0.3rem',
            borderRadius: '8px',
            boxShadow: 'var(--card-shadow)',
            zIndex: 10,
          }}
        >
          <button className="btn-ghost" onClick={handleZoomIn} title="Zoom In" style={{ padding: '0.3rem 0.5rem', fontWeight: 800 }}>
            +
          </button>
          <button className="btn-ghost" onClick={handleZoomOut} title="Zoom Out" style={{ padding: '0.3rem 0.5rem', fontWeight: 800 }}>
            −
          </button>
          <button className="btn-ghost" onClick={handleFit} title="Fit Graph" style={{ padding: '0.3rem 0.5rem' }}>
            ⛶
          </button>
          <button className="btn-ghost" onClick={handleReset} title="Reset View" style={{ padding: '0.3rem 0.5rem' }}>
            ↺
          </button>
        </div>

        {/* Compact Node Shape Legend Panel (Part 3) */}
        {showLegend && (
          <div
            style={{
              position: 'absolute',
              top: '16px',
              left: '16px',
              background: 'var(--bg-surface)',
              border: '1px solid var(--border-medium)',
              borderRadius: '8px',
              padding: '0.85rem 1rem',
              boxShadow: 'var(--card-shadow)',
              fontSize: '0.74rem',
              zIndex: 15,
              display: 'flex',
              flexDirection: 'column',
              gap: '0.5rem',
              maxWidth: '300px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ fontWeight: 700, color: 'var(--text-primary)' }}>Graph Legend</div>
              <button
                onClick={() => setShowLegend(false)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <span style={{ width: 14, height: 14, borderRadius: '50%', background: '#0284c7', border: '1.5px solid #38bdf8', display: 'inline-block' }} />
              <div>
                <strong>○ W</strong> = Wallet (Address)
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <span style={{ width: 13, height: 13, transform: 'rotate(45deg)', background: '#0891b2', border: '1.5px solid #22d3ee', display: 'inline-block' }} />
              <div>
                <strong>◇ TX</strong> = Transaction (TXID)
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <span style={{ width: 14, height: 14, borderRadius: '2px', background: '#4f46e5', border: '1.5px solid #818cf8', display: 'inline-block' }} />
              <div>
                <strong>⬡ IP</strong> = Observed IP Address
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <span style={{ width: 0, height: 0, borderLeft: '7px solid transparent', borderRight: '7px solid transparent', borderBottom: '14px solid #d97706', display: 'inline-block' }} />
              <div>
                <strong>△ ASN</strong> = Autonomous System Number
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <span style={{ width: 14, height: 14, borderRadius: '3px', background: '#7e22ce', border: '1.5px solid #c084fc', display: 'inline-block' }} />
              <div>
                <strong>▢ CC</strong> = Country
              </div>
            </div>

            <div
              style={{
                marginTop: '0.4rem',
                paddingTop: '0.4rem',
                borderTop: '1px solid var(--border-subtle)',
                fontSize: '0.68rem',
                color: 'var(--text-muted)',
                lineHeight: 1.4,
              }}
            >
              Graph relationships represent observed/correlated evidence from the selected dataset; they do not by themselves establish ownership or criminal attribution.
            </div>
          </div>
        )}

        {/* Loading Spinner */}
        {loading && (
          <div
            style={{
              position: 'absolute',
              inset: 0,
              background: 'rgba(0, 0, 0, 0.45)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem',
              color: 'var(--text-primary)',
              zIndex: 20,
            }}
          >
            <span className="status-dot online pulse" />
            <span style={{ fontSize: '0.85rem' }}>{t('loading_label')}</span>
          </div>
        )}

        {/* Error Alert */}
        {errorMsg && (
          <div
            style={{
              position: 'absolute',
              top: '16px',
              left: '50%',
              transform: 'translateX(-50%)',
              background: 'rgba(239, 68, 68, 0.9)',
              color: '#fff',
              padding: '0.4rem 0.8rem',
              borderRadius: '6px',
              fontSize: '0.78rem',
              zIndex: 25,
            }}
          >
            {errorMsg}
          </div>
        )}

        {/* Right-Hand Entity Details Drawer (Part 4, 12, 15) */}
        {selectedNode && (
          <div
            className="entity-drawer"
            style={{
              width: '400px',
              minWidth: '360px',
              maxWidth: '440px',
              flexShrink: 0,
              height: '100%',
              background: 'var(--bg-surface)',
              borderLeft: '1px solid var(--border-medium)',
              boxShadow: 'var(--card-shadow)',
              padding: '1.25rem',
              overflowY: 'auto',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              zIndex: 20,
            }}
          >
            <div>
              {/* Drawer Top Controls */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                <button
                  className="btn-secondary"
                  onClick={() => handleExpandNeighbors(selectedNode.id)}
                  style={{ fontSize: '0.72rem', padding: '0.25rem 0.55rem' }}
                >
                  + Expand Neighbors
                </button>
                <button
                  onClick={() => {
                    cyRef.current?.elements().removeClass('dimmed').removeClass('highlighted');
                    setSelectedNode(null);
                  }}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--text-muted)',
                    cursor: 'pointer',
                    fontSize: '1.2rem',
                    padding: '0.2rem',
                  }}
                >
                  ✕
                </button>
              </div>

              {/* Comprehensive Forensic Entity Investigation Summary Component */}
              <EntityInvestigationSummary
                entityType={selectedNode.label.toLowerCase() as any}
                entityId={selectedNode.canonical_id}
                datasetId={datasetId}
                wallets={wallets}
                correlations={correlations}
                riskFindings={riskFindings}
                behaviorFindings={behaviorFindings}
                anomalies={anomalies}
                graphMetrics={graphMetrics}
                clusters={clusters}
                networkObservations={networkObservations}
                compact={true}
                onSelectEntity={onSelectEntity}
              />
            </div>

            {/* Bottom Primary Action Button */}
            <div style={{ marginTop: '1.25rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border-subtle)' }}>
              <button
                className="btn-primary"
                onClick={() => onSelectEntity(selectedNode.label.toLowerCase() as any, selectedNode.canonical_id)}
                style={{ width: '100%', justifyContent: 'center', fontSize: '0.78rem' }}
              >
                Open Full Investigation Dossier →
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * useWebSocket Hook - Manages real-time WebSocket connection for pipeline updates.
 */

import { useEffect, useRef, useCallback } from 'react';
import useAppStore from '../store/useAppStore';

export default function useWebSocket() {
  const wsRef = useRef(null);
  const reconnectTimer = useRef(null);
  const { setWsConnected, setPipelineRunning, setCurrentNode, addNotification } = useAppStore();

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket('ws://localhost:8000/ws/pipeline');

      ws.onopen = () => {
        setWsConnected(true);
        console.log('[WS] Connected');
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          switch (data.event) {
            case 'pipeline_start':
              setPipelineRunning(true);
              setCurrentNode('start');
              addNotification({ type: 'info', message: 'Pipeline started' });
              break;
            case 'node_active':
              setCurrentNode(data.node);
              break;
            case 'node_complete':
              // Node completed, wait for next
              break;
            case 'pipeline_complete':
              setPipelineRunning(false);
              setCurrentNode(null);
              addNotification({
                type: 'success',
                message: `Pipeline completed: ${data.incidents || 0} incidents found`,
              });
              break;
            case 'pipeline_error':
              setPipelineRunning(false);
              setCurrentNode(null);
              addNotification({ type: 'error', message: `Pipeline error: ${data.error}` });
              break;
          }
        } catch (e) {
          console.error('[WS] Parse error:', e);
        }
      };

      ws.onclose = () => {
        setWsConnected(false);
        console.log('[WS] Disconnected, reconnecting in 5s...');
        reconnectTimer.current = setTimeout(connect, 5000);
      };

      ws.onerror = () => {
        ws.close();
      };

      wsRef.current = ws;
    } catch (e) {
      console.error('[WS] Connection error:', e);
      reconnectTimer.current = setTimeout(connect, 5000);
    }
  }, [setWsConnected, setPipelineRunning, setCurrentNode, addNotification]);

  useEffect(() => {
    connect();
    return () => {
      if (wsRef.current) wsRef.current.close();
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
    };
  }, [connect]);
}

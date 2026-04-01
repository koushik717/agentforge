import { useState, useEffect, useCallback } from 'react';

export function useApi(fetcher, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetcher();
      setData(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, deps);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return { data, loading, error, refetch };
}

export function usePolling(fetcher, intervalMs = 5000, deps = []) {
  const { data, loading, error, refetch } = useApi(fetcher, deps);

  useEffect(() => {
    const timer = setInterval(refetch, intervalMs);
    return () => clearInterval(timer);
  }, [refetch, intervalMs]);

  return { data, loading, error, refetch };
}

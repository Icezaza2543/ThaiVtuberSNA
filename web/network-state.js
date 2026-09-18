/* Pure selected-snapshot adapter. No network, clock-derived periods or fixture defaults. */
(function (root) {
  const attributes = ['subscribers', 'agency', 'status', 'priority', 'degree', 'betweenness', 'pagerank'];
  function periods(data) {
    const keys = data?.snapshots?.map(s => s.snapshot_id) || Object.keys(data?.slices || {});
    const years = [...new Set(keys.map(k => /^(?:yearly|cumulative)_(\d{4})$/.exec(k)?.[1]).filter(Boolean))].sort();
    return [...years.map(year => ({year, label: year})), {year: null, label: 'All-Time (Dated)'}];
  }
  function select(data, period, cumulative, roster) {
    const key = period ? `${cumulative ? 'cumulative' : 'yearly'}_${period}` : 'all_time';
    if (data?.dataset_version === 'expanded-v1') {
      const s = data.snapshots?.find(s => s.snapshot_id === key);
      if (!s || s.coverage_state === 'NO_SNAPSHOT') return {snapshot_id: key, nodes: [], edges: [], unknown_history: [], coverage_state: 'NO_SNAPSHOT'};
      const nodes = (s.nodes || []).filter(n => n.membership_evidence_refs?.length &&
        (n.visibility_state === 'EVIDENCED' && n.entity_type !== 'production_only' ||
         n.visibility_state === 'CREDIT_EVIDENCED' && n.entity_type === 'production_only'))
        .map(n => ({...n, ...Object.fromEntries(attributes.map(a => [a, n[a] ?? null]))}));
      const ids = new Set(nodes.map(n => n.id));
      return {...s, nodes, edges: (s.edges || []).filter(e => ids.has(e.source) && ids.has(e.target))};
    }
    // Frozen legacy exports have no reviewed identity membership. Keep their roster
    // only in an explicitly labelled context view; never turn it into historical fact.
    if (!period) return {snapshot_id: key, coverage_state: 'LEGACY_UNVERIFIED',
      nodes: roster.map(n => ({...n})), edges: data?.slices?.all_time?.edges || [],
      unknown_history: roster.map(n => n.id)};
    return {snapshot_id: key, coverage_state: data?.slices?.[key] ? 'IDENTITY_NOT_REVIEWED' : 'NO_SNAPSHOT',
      nodes: [], edges: [], unknown_history: roster.map(n => n.id)};
  }
  root.TemporalState = {periods, select};
  if (typeof module !== 'undefined') module.exports = root.TemporalState;
})(globalThis);

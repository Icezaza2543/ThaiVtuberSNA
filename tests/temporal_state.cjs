const assert = require('node:assert/strict');
const {periods, select} = require('../web/temporal-state.js');
const node = {id:'synthetic-a', label:'A', visibility_state:'EVIDENCED', membership_evidence_refs:['e']};
const data = {dataset_version:'expanded-v1', snapshots:[
  {snapshot_id:'yearly_2020', nodes:[node], edges:[], coverage_state:'PARTIAL'},
  {snapshot_id:'yearly_2027', nodes:[], edges:[], coverage_state:'PARTIAL'}]};
assert.deepEqual(periods(data).map(p=>p.year), ['2020','2027',null]);
assert.equal(select(data,'2020',false,[]).nodes[0].subscribers,null);
assert.equal(select(data,'2021',false,[]).coverage_state,'NO_SNAPSHOT');
assert.equal(select(data,'2028',false,[]).nodes.length,0);
assert.equal(select({slices:{yearly_2020:{edges:[]}}},'2020',false,[node]).unknown_history.length,1);
console.log('temporal state: 5 assertions passed');

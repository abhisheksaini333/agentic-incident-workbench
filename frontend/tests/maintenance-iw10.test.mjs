import {test} from 'node:test';
import assert from 'node:assert/strict';
import {Api} from '../src/api.mjs';
test('malformed response stays an error and expiry callback still runs',async()=>{
 let expired=0;let response={ok:true,status:200,json:async()=>{throw new SyntaxError('bad json');}};
 const api=new Api('private',()=>expired++,async()=>response);
 await assert.rejects(api.call('/api/me'),/unreadable/);
 response={ok:false,status:401,json:async()=>null};await assert.rejects(api.call('/api/me'),/could not be completed/);assert.equal(expired,1);
 response={ok:true,status:200,json:async()=>null};await assert.rejects(api.call('/api/me'),/unreadable/);
});

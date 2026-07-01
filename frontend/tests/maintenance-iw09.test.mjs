import {test} from 'node:test';
import assert from 'node:assert/strict';
import {Api} from '../src/api.mjs';
test('encoded traversal cannot carry bearer outside local API and redirects are refused',async()=>{
 let calls=0,options; const api=new Api('private',()=>{},async(path,opts)=>{calls++;options=opts;return {ok:true,status:200,json:async()=>({ok:true})};});
 for(const path of ['/api/%2e%2e/private','/api/%5cprivate','/api/%ZZ','/api/hello\n']) await assert.rejects(api.call(path),/API path/);
 assert.equal(calls,0);await api.call('/api/me');assert.equal(options.redirect,'error');
});

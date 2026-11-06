(function(){var K='tmn-plan-v1',s={},boxes=document.querySelectorAll('input[type=checkbox][data-k]'),note=document.getElementById('save-note');
try{var v=JSON.parse(localStorage.getItem(K)||'{}');if(v&&typeof v==='object'&&!Array.isArray(v))s=v}catch(e){}
function save(){try{localStorage.setItem(K,JSON.stringify(s));note.textContent=''}catch(e){note.textContent='Your ticks could not be saved in this browser (private browsing?). They will be lost when you close this page.'}}
boxes.forEach(function(c){c.checked=s[c.dataset.k]===true;c.addEventListener('change',function(){s[c.dataset.k]=c.checked;save()})});
document.getElementById('print').addEventListener('click',function(){window.print()});
document.getElementById('clear').addEventListener('click',function(){s={};try{localStorage.removeItem(K)}catch(e){}boxes.forEach(function(c){c.checked=false})})})();

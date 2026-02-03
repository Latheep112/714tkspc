// Theme toggle and small UX helpers
(function(){
  var body = document.body;
  var btn = document.getElementById('themeToggle');
  function applyTheme(t){
    var isDark = t === 'dark';
    body.classList.toggle('dark', isDark);
    var nav = document.querySelector('.navbar');
    if(nav){
      if(isDark){ nav.classList.remove('navbar-light','bg-light','bg-tkspc'); nav.classList.add('navbar-dark','bg-dark'); }
      else { nav.classList.remove('navbar-dark','bg-dark'); nav.classList.add('navbar-dark','bg-tkspc'); }
    }
    if(btn){ btn.textContent = isDark ? 'Light Mode' : 'Dark Mode'; }
  }
  var saved = localStorage.getItem('theme');
  applyTheme(saved || 'light');
  if(btn){
    btn.addEventListener('click', function(){
      var current = body.classList.contains('dark') ? 'dark' : 'light';
      var next = current === 'dark' ? 'light' : 'dark';
      localStorage.setItem('theme', next);
      applyTheme(next);
    });
  }
  var compactBtn = document.getElementById('compactToggle');
  function applyCompact(val){
    var on = val === 'on';
    body.classList.toggle('compact', on);
    if(compactBtn){ compactBtn.textContent = on ? 'Compact On' : 'Compact Mode'; }
  }
  var compactSaved = localStorage.getItem('compact') || 'off';
  applyCompact(compactSaved);
  if(compactBtn){
    compactBtn.addEventListener('click', function(){
      var next = body.classList.contains('compact') ? 'off' : 'on';
      localStorage.setItem('compact', next);
      applyCompact(next);
    });
  }
  // Show Bootstrap toasts for flashed messages
  (function(){
    var toasts = document.querySelectorAll('.toast');
    if (typeof bootstrap !== 'undefined' && toasts.length) {
      toasts.forEach(function(el){
        try { new bootstrap.Toast(el, { autohide: true, delay: 4000 }).show(); } catch(e){}
      });
    } else if (window.jQuery) {
      var $ = window.jQuery;
      $(function(){ $('.toast').toast('show'); });
    }
  })();
  // Tooltips for navbar icons on small screens
  (function(){
    if (typeof bootstrap === 'undefined') return;
    function initNavTooltips(){
      var isSmall = window.matchMedia('(max-width: 768px)').matches;
      var links = document.querySelectorAll('.navbar .nav-link[data-bs-toggle="tooltip"]');
      links.forEach(function(link){
        var tip = bootstrap.Tooltip.getInstance(link);
        if (tip) { tip.dispose(); }
        new bootstrap.Tooltip(link, { placement: 'bottom', trigger: isSmall ? 'hover focus' : 'manual' });
      });
    }
    initNavTooltips();
    window.addEventListener('resize', function(){ initNavTooltips(); });
  })();
  // Remove initial loading skeletons once DOM is ready
  document.addEventListener('DOMContentLoaded', function(){
    body.classList.remove('loading');
  });
})();

// Password toggle
document.addEventListener('click', function(e){
  if(e.target && e.target.matches('[data-toggle="password"]')){
    var input = document.querySelector(e.target.getAttribute('data-target'));
    if(input){ input.type = input.type === 'password' ? 'text' : 'password'; }
  }
});

// Lightweight table sort and client-side filter
(function(){
  function getCellText(td){ return (td.textContent || td.innerText || '').trim(); }
  function compare(a, b){
    var na = parseFloat(a), nb = parseFloat(b);
    if(!isNaN(na) && !isNaN(nb)) return na - nb;
    return a.localeCompare(b);
  }
  function sortTable(table, colIndex, asc){
    var tbody = table.tBodies[0];
    var rows = Array.prototype.slice.call(tbody.querySelectorAll('tr'));
    rows.sort(function(r1, r2){
      var a = getCellText(r1.children[colIndex] || {});
      var b = getCellText(r2.children[colIndex] || {});
      var cmp = compare(a, b);
      return asc ? cmp : -cmp;
    });
    rows.forEach(function(r){ tbody.appendChild(r); });
  }
  document.addEventListener('click', function(e){
    var th = e.target.closest('th');
    if(!th) return;
    var table = th.closest('table');
    if(!table || !table.classList.contains('js-table')) return;
    var index = Array.prototype.indexOf.call(th.parentNode.children, th);
    var asc = !(th.dataset.sortDir === 'asc');
    sortTable(table, index, asc);
    th.dataset.sortDir = asc ? 'asc' : 'desc';
  });
  document.addEventListener('input', function(e){
    if(!e.target.classList.contains('js-table-filter')) return;
    var targetSel = e.target.getAttribute('data-target');
    var table = document.querySelector(targetSel);
    if(!table) return;
    var q = (e.target.value || '').toLowerCase();
    Array.prototype.forEach.call(table.tBodies[0].rows, function(row){
      var txt = row.textContent.toLowerCase();
      row.style.display = txt.indexOf(q) !== -1 ? '' : 'none';
    });
  });
})();

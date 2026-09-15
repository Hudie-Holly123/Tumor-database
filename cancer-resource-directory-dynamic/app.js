(function () {
  'use strict';

  const data = window.CANCER_RESOURCE_DATA;
  if (!data) {
    document.body.innerHTML = '<main style="padding:40px;font-family:system-ui"><h1>Data file not found</h1><p>Run <code>python scripts/build_data.py ... data/resources.json</code> and rebuild the page.</p></main>';
    return;
  }

  const $ = (id) => document.getElementById(id);
  const homeView = $('homeView');
  const categoryView = $('categoryView');
  const categoryGrid = $('categoryGrid');
  const categoryTitle = $('categoryTitle');
  const categoryEyebrow = $('categoryEyebrow');
  const categoryDescription = $('categoryDescription');
  const categorySearch = $('categorySearch');
  const globalSearch = $('globalSearch');
  const usageFilter = $('usageFilter');
  const resultCount = $('resultCount');
  const tbody = document.querySelector('#resourceTable tbody');
  const modal = $('modal');
  const modalTitle = $('modalTitle');
  const modalCategory = $('modalCategory');
  const modalFields = $('modalFields');
  const officialLink = $('officialLink');
  const copyLink = $('copyLink');

  $('uniqueCount').textContent = data.uniqueResourceNames.toLocaleString();
  $('entryCount').textContent = data.totalCategoryEntries.toLocaleString();
  $('categoryCount').textContent = data.categories.length.toLocaleString();
  const verified = data.verificationCount || 0;
  const verifiedEl = $('verifiedCount');
  if (verifiedEl) verifiedEl.textContent = verified.toLocaleString();
  $('footerMeta').textContent = `Curated snapshot: ${data.lastChecked}${data.lastLiveVerification ? ` · Live verification: ${data.lastLiveVerification}` : ''}`;

  const fieldOrder = [
    'Full Name', 'Resource Type', 'Year Started', 'Cancer Coverage', 'Data Available',
    'Data Amount', 'Clinical Data', 'Treatment / Response / Outcome', 'Raw / Processed Data',
    'Access Type', 'Cost', 'Usage Score (1–10)', 'Main Advantage', 'Main Limitation',
    'Official / Access URL', 'Source / Provenance', 'Last Checked', 'Notes'
  ];

  const categoryDescriptions = {
    'Cancer Genomics & Multi-omics / Patient Cohorts': 'Large patient/tumor cohorts with genomic, transcriptomic, epigenomic and multi-omic measurements.',
    'General Omics Repositories Containing Cancer Data': 'General repositories where individual cancer studies and their sequencing or omics datasets are deposited.',
    'Cancer Single-Cell Data Resources': 'Tumor scRNA-seq, snRNA-seq and single-cell tumor microenvironment resources.',
    'Spatial Transcriptomics & Spatial Omics': 'Spatial RNA, imaging-based spatial assays and multimodal spatial tumor resources.',
    'Cancer Proteomics & Proteogenomics': 'Tumor protein abundance, phosphoproteomics, mass spectrometry and proteogenomics.',
    'Cancer Models & Functional Genomics / CRISPR': 'Cancer cell lines, organoids, PDX models and functional/genetic dependency screens.',
    'Cancer Drug Response & Resistance': 'Drug sensitivity, combination therapy, perturbation, resistance and pharmacogenomic resources.',
    'Cancer Genomic Alterations & Processed Data Portals': 'Processed mutation, CNV, expression and cancer genomic exploration portals.',
    'Cancer Imaging & Digital Pathology': 'Radiology, whole-slide imaging, histopathology and multiplex tissue imaging resources.',
    'Cancer Clinical / Epidemiology / Outcomes': 'Clinical cohorts, cancer registries, trial information, treatment and patient outcomes.',
    'Cancer Immunology & Immunotherapy': 'Tumor immune microenvironment, immunogenomics, repertoire and immunotherapy-response resources.',
    'Cancer Microbiome': 'Tumor-associated and gut microbiome datasets relevant to cancer.',
    'Cancer Metabolomics & Lipidomics': 'Cancer metabolite, lipid and mass-spectral datasets and reference resources.',
    'Extracellular Vesicle / Liquid Biopsy / CTC / ctDNA': 'EV/exosome, ctDNA, cfDNA, cfRNA and circulating-tumor-cell resources.',
    'Cancer-Type-Specific & Other Specialized Cancer Resources': 'Disease-specific and highly specialized cancer datasets and databases.',
    'Supporting Cancer Bioinformatics Knowledge Resources': 'Reference resources used to interpret cancer datasets, genes, proteins, pathways and variants.'
  };

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#039;');
  }

  function score(value) {
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
  }

  function rowKey(categoryId, index) {
    return `${categoryId}::${index}`;
  }

  function findByKey(key) {
    const [categoryId, rawIndex] = key.split('::');
    const category = data.categories.find(c => c.id === categoryId);
    const index = Number(rawIndex);
    return category && category.entries[index] ? { category, item: category.entries[index] } : null;
  }

  function searchableText(item) {
    return Object.values(item).join(' ').toLowerCase();
  }

  function renderCategories(filter = '') {
    const q = filter.trim().toLowerCase();
    categoryGrid.innerHTML = '';
    data.categories.forEach((category, index) => {
      const corpus = `${category.title} ${category.entries.map(searchableText).join(' ')}`.toLowerCase();
      if (q && !corpus.includes(q)) return;
      const card = document.createElement('button');
      card.className = 'category-card';
      card.type = 'button';
      card.innerHTML = `
        <div class="num">${String(index + 1).padStart(2, '0')}</div>
        <h3>${escapeHtml(category.title)}</h3>
        <p>${escapeHtml(categoryDescriptions[category.title] || 'Cancer-related data resources in this category.')}</p>
        <div class="category-count">${category.count} category entries</div>`;
      card.addEventListener('click', () => navigateCategory(category.id));
      categoryGrid.appendChild(card);
    });
  }

  function navigateCategory(id) {
    history.pushState({}, '', `#category=${encodeURIComponent(id)}`);
    showCategory(id);
  }

  function showCategory(id) {
    const category = data.categories.find(c => c.id === id);
    if (!category) { showHome(); return; }
    homeView.classList.add('hidden');
    categoryView.classList.remove('hidden');
    categoryEyebrow.textContent = 'Category';
    categoryTitle.textContent = category.title;
    categoryDescription.textContent = categoryDescriptions[category.title] || '';
    categorySearch.value = '';
    usageFilter.value = '0';
    renderTable(category);
    window.scrollTo({ top: 0, behavior: 'instant' });
  }

  function showHome() {
    homeView.classList.remove('hidden');
    categoryView.classList.add('hidden');
    globalSearch.focus();
    history.pushState({}, '', window.location.pathname + window.location.search);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function filteredEntries(category) {
    const q = categorySearch.value.trim().toLowerCase();
    const minUsage = Number(usageFilter.value || 0);
    return category.entries
      .map((item, index) => ({ item, index }))
      .filter(({ item }) => !q || searchableText(item).includes(q))
      .filter(({ item }) => minUsage === 0 || (score(item['Usage Score (1–10)']) || 0) >= minUsage);
  }

  function renderTable(category) {
    const rows = filteredEntries(category);
    tbody.innerHTML = '';
    rows.forEach(({ item, index }) => {
      const tr = document.createElement('tr');
      const key = rowKey(category.id, index);
      const usage = score(item['Usage Score (1–10)']);
      tr.innerHTML = `
        <td><button class="resource-link" data-key="${escapeHtml(key)}">${escapeHtml(item['Resource / Platform'])}</button></td>
        <td>${escapeHtml(item['Resource Type'])}</td>
        <td>${escapeHtml(item['Year Started'])}</td>
        <td>${escapeHtml(item['Cancer Coverage'])}</td>
        <td>${escapeHtml(item['Data Available'])}</td>
        <td>${escapeHtml(item['Data Amount'])}</td>
        <td>${escapeHtml(item['Clinical Data'])}<br><br>${escapeHtml(item['Treatment / Response / Outcome'])}</td>
        <td>${escapeHtml(item['Access Type'])}</td>
        <td>${escapeHtml(item['Cost'])}</td>
        <td>${usage == null ? '—' : `<span class="badge">${usage}</span>`}</td>`;
      tbody.appendChild(tr);
    });
    resultCount.textContent = `${rows.length} of ${category.count} entries`;
  }

  function openModal(key) {
    const found = findByKey(key);
    if (!found) return;
    const { category, item } = found;
    modalTitle.textContent = item['Resource / Platform'] || '';
    modalCategory.textContent = category.title;
    const url = item['Official / Access URL'] || '';
    officialLink.href = url || '#';
    officialLink.classList.toggle('hidden', !url);
    copyLink.classList.toggle('hidden', !url);
    copyLink.onclick = async () => {
      try {
        await navigator.clipboard.writeText(url);
        copyLink.textContent = 'Copied';
        setTimeout(() => copyLink.textContent = 'Copy official URL', 1200);
      } catch (_) {
        window.prompt('Copy this URL:', url);
      }
    };

    modalFields.innerHTML = '';
    fieldOrder.forEach(field => {
      if (!(field in item)) return;
      const value = item[field];
      if (value === '' || value == null) return;
      const div = document.createElement('div');
      const full = ['Data Available', 'Data Amount', 'Clinical Data', 'Treatment / Response / Outcome', 'Main Advantage', 'Main Limitation', 'Official / Access URL', 'Source / Provenance', 'Notes'].includes(field);
      div.className = `detail-item${full ? ' full' : ''}`;
      let valueHtml = escapeHtml(value);
      if (field === 'Official / Access URL') {
        valueHtml = `<a href="${escapeHtml(value)}" target="_blank" rel="noopener">${escapeHtml(value)}</a>`;
      }
      div.innerHTML = `<div class="detail-label">${escapeHtml(field)}</div><div class="detail-value">${valueHtml}</div>`;
      modalFields.appendChild(div);
    });
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
  }

  function closeModal() {
    modal.classList.add('hidden');
    document.body.style.overflow = '';
  }

  function exportCsv(items, filename) {
    const columns = ['Category', ...fieldOrder];
    const lines = [columns.map(csvCell).join(',')];
    items.forEach(({ category, item }) => {
      lines.push([category.title, ...fieldOrder.map(f => item[f] ?? '')].map(csvCell).join(','));
    });
    const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = filename; a.click(); URL.revokeObjectURL(url);
  }

  function csvCell(value) {
    const s = String(value == null ? '' : value).replaceAll('"', '""');
    return `"${s}"`;
  }

  $('backHome').addEventListener('click', showHome);
  categorySearch.addEventListener('input', () => {
    const id = new URLSearchParams(window.location.hash.slice(1)).get('category');
    const category = data.categories.find(c => c.id === id);
    if (category) renderTable(category);
  });
  usageFilter.addEventListener('change', () => {
    const id = new URLSearchParams(window.location.hash.slice(1)).get('category');
    const category = data.categories.find(c => c.id === id);
    if (category) renderTable(category);
  });
  globalSearch.addEventListener('input', () => {
    renderCategories(globalSearch.value);
  });
  document.addEventListener('click', (event) => {
    const button = event.target.closest('.resource-link');
    if (button) openModal(button.dataset.key);
  });
  $('modalClose').addEventListener('click', closeModal);
  $('modalBackdrop').addEventListener('click', closeModal);
  document.addEventListener('keydown', (event) => { if (event.key === 'Escape') closeModal(); });

  $('exportAll').addEventListener('click', () => {
    const items = [];
    data.categories.forEach(category => category.entries.forEach(item => items.push({ category, item })));
    exportCsv(items, 'cancer-data-resource-directory.csv');
  });

  window.addEventListener('popstate', renderRoute);
  window.addEventListener('hashchange', renderRoute);

  function renderRoute() {
    const hash = new URLSearchParams(window.location.hash.slice(1));
    const id = hash.get('category');
    const resource = hash.get('resource');
    if (resource) openModal(resource);
    if (id) showCategory(id); else showHomeInitial();
  }

  function showHomeInitial() {
    homeView.classList.remove('hidden');
    categoryView.classList.add('hidden');
  }

  renderCategories('');
  renderRoute();
})();

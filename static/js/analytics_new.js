const ANALYTICS_ENDPOINT = '/analytics/data/';
const SYNC_ENDPOINT = '/analytics/sync/';
const REFRESH_INTERVAL_MS = 10000;
let refreshTimer = null;

const statusEl = document.getElementById('analyticsStatus');
const lastUpdatedEl = document.getElementById('lastUpdated');
const refreshButton = document.getElementById('refreshButton');
const syncButton = document.getElementById('syncButton');
const downloadButton = document.getElementById('downloadButton');

function setStatus(message, type = 'info') {
  if (!statusEl) return;
  statusEl.textContent = message;
  statusEl.className = `status ${type}`;
}

function setLastUpdated(timestamp) {
  if (!lastUpdatedEl) return;
  lastUpdatedEl.textContent = `Last updated: ${new Date(timestamp).toLocaleString()}`;
}

function updateMetrics(data) {
  // Calculate and update top metric cards
  const totalRespondents = data.descriptive_stats?.Age?.count || 0;
  document.getElementById('totalRespondents').textContent = totalRespondents;
  
  const avgAge = data.descriptive_stats?.Age?.mean?.toFixed(1) || '-';
  document.getElementById('avgAge').textContent = avgAge;
  
  const avgFuelCost = data.descriptive_stats?.['What is your approximate weekly fuel expense? (PKR)']?.mean?.toFixed(0) || '-';
  document.getElementById('avgFuelCost').textContent = `PKR ${avgFuelCost}`;
  
  const fuelImpactScore = data.descriptive_stats?.['Rising fuel prices affect my daily travel decisions']?.mean?.toFixed(2) || '-';
  document.getElementById('fuelImpactScore').textContent = fuelImpactScore;
  
  // Calculate awareness rate
  const awareness = data.awareness?.subsidy_awareness || {};
  const yesCount = awareness.Yes || awareness.YES || 0;
  const totalAwareness = Object.values(awareness).reduce((a, b) => a + b, 0);
  const awarenessRate = totalAwareness > 0 ? ((yesCount / totalAwareness) * 100).toFixed(0) + '%' : '-';
  document.getElementById('awarenessRate').textContent = awarenessRate;
  
  document.getElementById('generatedTime').textContent = new Date(data.generated_at).toLocaleString();
}

// ════════════════════════════════════════════════════════════════
// DESCRIPTIVE STATISTICS
// ════════════════════════════════════════════════════════════════
function renderDescriptiveStats(stats) {
  const container = document.getElementById('descriptiveStatsChart');
  container.innerHTML = '';
  
  if (!stats || Object.keys(stats).length === 0) {
    container.innerHTML = '<p>No descriptive statistics available</p>';
    return;
  }
  
  const table = document.createElement('div');
  table.style.overflowX = 'auto';
  
  let html = '<table style="width:100%; border-collapse: collapse; font-size: 12px;">';
  html += '<tr style="background: #e0f2fe;"><th style="border: 1px solid #bae6fd; padding: 8px; text-align: left;"><strong>Variable</strong></th>';
  html += '<th style="border: 1px solid #bae6fd; padding: 8px;">N</th>';
  html += '<th style="border: 1px solid #bae6fd; padding: 8px;">Mean</th>';
  html += '<th style="border: 1px solid #bae6fd; padding: 8px;">Median</th>';
  html += '<th style="border: 1px solid #bae6fd; padding: 8px;">Mode</th>';
  html += '<th style="border: 1px solid #bae6fd; padding: 8px;">Std Dev</th>';
  html += '<th style="border: 1px solid #bae6fd; padding: 8px;">Variance</th>';
  html += '<th style="border: 1px solid #bae6fd; padding: 8px;">Min</th>';
  html += '<th style="border: 1px solid #bae6fd; padding: 8px;">Max</th></tr>';
  
  Object.entries(stats).forEach(([varName, s]) => {
    if (s && s.count > 0) {
      html += `<tr style="background: #fff; border-bottom: 1px solid #e0e7ff;">`;
      html += `<td style="border: 1px solid #bae6fd; padding: 8px;"><strong>${varName.substring(0, 30)}</strong></td>`;
      html += `<td style="border: 1px solid #bae6fd; padding: 8px; text-align: center;">${s.count}</td>`;
      html += `<td style="border: 1px solid #bae6fd; padding: 8px; text-align: center;">${s.mean?.toFixed(2)}</td>`;
      html += `<td style="border: 1px solid #bae6fd; padding: 8px; text-align: center;">${s.median?.toFixed(2)}</td>`;
      html += `<td style="border: 1px solid #bae6fd; padding: 8px; text-align: center;">${s.mode?.toFixed(2)}</td>`;
      html += `<td style="border: 1px solid #bae6fd; padding: 8px; text-align: center;">${s.std_dev?.toFixed(2)}</td>`;
      html += `<td style="border: 1px solid #bae6fd; padding: 8px; text-align: center;">${s.variance?.toFixed(2)}</td>`;
      html += `<td style="border: 1px solid #bae6fd; padding: 8px; text-align: center;">${s.min?.toFixed(2)}</td>`;
      html += `<td style="border: 1px solid #bae6fd; padding: 8px; text-align: center;">${s.max?.toFixed(2)}</td>`;
      html += `</tr>`;
    }
  });
  
  html += '</table>';
  table.innerHTML = html;
  container.appendChild(table);
}

// ════════════════════════════════════════════════════════════════
// DEMOGRAPHICS
// ════════════════════════════════════════════════════════════════
function renderDemographics(demographics) {
  const container = document.getElementById('demographicsCharts');
  container.innerHTML = '';
  
  Object.entries(demographics).forEach(([question, data]) => {
    if (!data || Object.keys(data).length === 0) return;
    
    const chartId = `demo_${question.replace(/[^a-zA-Z0-9]/g, '_')}`;
    const card = document.createElement('div');
    card.id = chartId;
    card.className = 'section-chart';
    card.innerHTML = `<h3>${question}</h3><div id="${chartId}_plot"></div>`;
    
    container.appendChild(card);
    
    const categories = Object.keys(data);
    const values = Object.values(data);
    
    const chartType = categories.length > 2 ? 'bar' : 'pie';
    
    if (chartType === 'pie') {
      Plotly.react(`${chartId}_plot`, [{
        labels: categories,
        values,
        type: 'pie',
        textinfo: 'percent+label',
        marker: { colors: ['#8b5cf6', '#ec4899', '#f59e0b', '#06b6d4', '#10b981'] },
      }], {
        margin: { t: 20, b: 20, l: 20, r: 20 },
        height: 350,
      });
    } else {
      Plotly.react(`${chartId}_plot`, [{
        type: 'bar',
        x: categories,
        y: values,
        marker: { color: '#8b5cf6' },
      }], {
        margin: { t: 20, b: 80 },
        xaxis: { automargin: true },
        yaxis: { title: 'Count' },
        height: 350,
      });
    }
  });
}

// ════════════════════════════════════════════════════════════════
// REGRESSION
// ════════════════════════════════════════════════════════════════
function renderRegression(regression) {
  if (!regression || !regression.x || regression.x.length === 0) return;
  
  const container = document.getElementById('regressionChart');
  container.innerHTML = `<h3>📉 Regression Analysis</h3><div id="regressionPlot"></div>`;
  
  const x = regression.x;
  const y = regression.y;
  const x_line = regression.x_line || x.slice().sort((a, b) => a - b);
  const y_line = x_line.map(val => regression.slope * val + regression.intercept);
  
  Plotly.react('regressionPlot', [
    {
      x, y,
      mode: 'markers',
      type: 'scatter',
      name: 'Data points',
      marker: { color: '#ec4899', size: 8, opacity: 0.7 },
    },
    {
      x: x_line,
      y: y_line,
      mode: 'lines',
      type: 'scatter',
      name: 'Trend line',
      line: { color: '#ef4444', width: 3 },
    },
  ], {
    margin: { t: 20, b: 60, l: 60, r: 20 },
    xaxis: { title: regression.x_label || 'X Variable', automargin: true },
    yaxis: { title: regression.y_label || 'Y Variable' },
    height: 400,
    showlegend: true,
  });
  
  const stats = document.createElement('div');
  stats.style.cssText = 'margin-top: 10px; padding: 10px; background: #fef3c7; border-radius: 4px; font-size: 11px;';
  stats.innerHTML = `
    <strong>${regression.equation}</strong><br>
    R² = ${regression.r_squared.toFixed(4)} | p = ${regression.p_value.toFixed(4)} | ${regression.significance}
  `;
  container.appendChild(stats);
}

// ════════════════════════════════════════════════════════════════
// CORRELATIONS
// ════════════════════════════════════════════════════════════════
function renderCorrelations(correlations) {
  const container = document.getElementById('correlationChart');
  container.innerHTML = '<h3>📊 Correlation Matrix (Pearson r)</h3><div id="correlationTable"></div>';
  
  const table = document.createElement('div');
  table.style.overflowX = 'auto';
  
  let html = '<table style="width:100%; border-collapse: collapse; font-size: 11px;">';
  html += '<tr style="background: #f3e5f5;"><th style="border: 1px solid #e9d5ff; padding: 6px; text-align: left;"><strong>Variable Pair</strong></th>';
  html += '<th style="border: 1px solid #e9d5ff; padding: 6px;">Pearson r</th>';
  html += '<th style="border: 1px solid #e9d5ff; padding: 6px;">Strength</th>';
  html += '<th style="border: 1px solid #e9d5ff; padding: 6px;">p-value</th></tr>';
  
  Object.entries(correlations).forEach(([pair, corr]) => {
    const sig = corr.p_value < 0.05;
    html += `<tr style="background: #fff;">`;
    html += `<td style="border: 1px solid #e9d5ff; padding: 6px;"><strong>${pair.substring(0, 30)}</strong></td>`;
    html += `<td style="border: 1px solid #e9d5ff; padding: 6px; text-align: center;"><strong>${corr.pearson_r.toFixed(3)}</strong></td>`;
    html += `<td style="border: 1px solid #e9d5ff; padding: 6px; text-align: center;">${corr.strength}</td>`;
    html += `<td style="border: 1px solid #e9d5ff; padding: 6px; text-align: center; color: ${sig ? '#10b981' : '#f59e0b'};"><strong>${corr.p_value.toFixed(4)}</strong></td>`;
    html += `</tr>`;
  });
  
  html += '</table>';
  document.getElementById('correlationTable').innerHTML = html;
}

// ════════════════════════════════════════════════════════════════
// ANOVA
// ════════════════════════════════════════════════════════════════
function renderANOVA(anova) {
  if (!anova || !anova.f_statistic) return;
  
  const container = document.getElementById('anovaChart');
  container.innerHTML = `<h3>📈 ANOVA: ${anova.groups.join(', ')}</h3><div id="anovaPlot"></div>`;
  
  const traces = anova.groups.map(group => ({
    y: [anova.group_means[group]],
    error_y: { type: 'data', array: [anova.group_stds[group]], visible: true },
    name: group,
    type: 'bar',
    marker: { color: '#f59e0b' },
  }));
  
  Plotly.react('anovaPlot', traces, {
    margin: { t: 20, b: 80, l: 50, r: 20 },
    xaxis: { automargin: true },
    yaxis: { title: 'Mean' },
    height: 350,
    showlegend: true,
  });
  
  const stats = document.createElement('div');
  stats.style.cssText = 'margin-top: 10px; padding: 10px; background: #fef3c7; border-radius: 4px; font-size: 11px;';
  stats.innerHTML = `F = ${anova.f_statistic.toFixed(3)} | p = ${anova.p_value.toFixed(4)} | <strong>${anova.significance}</strong>`;
  container.appendChild(stats);
}

// ════════════════════════════════════════════════════════════════
// CHI-SQUARE
// ════════════════════════════════════════════════════════════════
function renderChiSquare(chiSquareData) {
  const container = document.getElementById('chiSquareCharts');
  container.innerHTML = '';
  
  Object.entries(chiSquareData).forEach(([dim, data]) => {
    const chartCard = document.createElement('div');
    chartCard.className = 'section-chart';
    chartCard.innerHTML = `<h3>χ² Test: ${dim}</h3><div id="chi_${dim.replace(/[^a-zA-Z0-9]/g, '_')}_plot"></div>`;
    container.appendChild(chartCard);
    
    const chartId = `chi_${dim.replace(/[^a-zA-Z0-9]/g, '_')}_plot`;
    
    // Use the properly formatted arrays from backend
    const z = data.z || [];
    const x = data.x || [];
    const y = data.y || [];
    
    Plotly.react(chartId, [{
      z, x, y,
      type: 'heatmap',
      colorscale: 'Viridis',
    }], {
      margin: { t: 20, b: 80, l: 100, r: 20 },
      height: 300,
    });
    
    const stats = document.createElement('p');
    stats.style.cssText = 'margin: 8px 0 0; padding: 6px; background: #fef3c7; border-radius: 4px; font-size: 10px;';
    stats.innerHTML = `χ² = ${data.chi2.toFixed(3)} | p = ${data.p_value.toFixed(4)} | ${data.p_value < 0.05 ? '<span style="color: #10b981;"><strong>Significant</strong></span>' : 'Not Significant'}`;
    chartCard.appendChild(stats);
  });
}

// ════════════════════════════════════════════════════════════════
// AWARENESS
// ════════════════════════════════════════════════════════════════
function renderAwareness(awareness) {
  if (!awareness || !awareness.subsidy_awareness) return;
  
  const container = document.getElementById('awarenessChart');
  container.innerHTML = '<h3>💡 Subsidy Program Awareness</h3><div id="awarenessPlot"></div>';
  
  const data = awareness.subsidy_awareness;
  Plotly.react('awarenessPlot', [{
    labels: Object.keys(data),
    values: Object.values(data),
    type: 'pie',
    textinfo: 'percent+label',
    marker: { colors: ['#10b981', '#ef4444', '#f59e0b'] },
  }], {
    margin: { t: 20, b: 20, l: 20, r: 20 },
    height: 350,
  });
}

// ════════════════════════════════════════════════════════════════
// PERCEPTION
// ════════════════════════════════════════════════════════════════
function renderPerception(perception) {
  if (!perception || !perception.distributions) return;
  
  const container = document.getElementById('perceptionChart');
  container.innerHTML = '<h3>💭 Digital System Perception (Likert)</h3><div id="perceptionPlot"></div>';
  
  const questions = Object.keys(perception.distributions);
  const traces = [];
  const responses = new Set();
  
  questions.forEach(q => {
    Object.keys(perception.distributions[q]).forEach(r => responses.add(r));
  });
  
  Array.from(responses).sort().forEach(resp => {
    traces.push({
      x: questions.map(q => q.substring(0, 25)),
      y: questions.map(q => perception.distributions[q][resp] || 0),
      name: String(resp),
      type: 'bar',
    });
  });
  
  Plotly.react('perceptionPlot', traces, {
    barmode: 'stack',
    margin: { t: 20, b: 100, l: 50, r: 20 },
    xaxis: { tickangle: -25, automargin: true },
    yaxis: { title: 'Count' },
    height: 350,
    showlegend: true,
  });
}

// ════════════════════════════════════════════════════════════════
// MAIN RENDER
// ════════════════════════════════════════════════════════════════
function renderAnalytics(data) {
  if (data.error) {
    setStatus(data.error, 'error');
    return;
  }
  
  setStatus('✅ Analysis complete', 'success');
  setLastUpdated(data.generated_at);
  updateMetrics(data);
  
  if (data.descriptive_stats) renderDescriptiveStats(data.descriptive_stats);
  if (data.demographics) renderDemographics(data.demographics);
  if (data.regression) renderRegression(data.regression);
  if (data.correlations && Object.keys(data.correlations).length > 0) renderCorrelations(data.correlations);
  if (data.anova) renderANOVA(data.anova);
  if (data.chi_square && Object.keys(data.chi_square).length > 0) renderChiSquare(data.chi_square);
  if (data.awareness) renderAwareness(data.awareness);
  if (data.subsidy_perception) renderPerception(data.subsidy_perception);
  if (data.hypothesis_tests?.t_test) {
    renderHypothesisTests(data.hypothesis_tests.t_test);
  }
  if (data.qualitative_insights) {
    renderQualitativeInsights(data.qualitative_insights);
  }
  if (data.analysis_metadata) {
    updateAnalysisMetadata(data.analysis_metadata);
  }
}

async function fetchAnalytics() {
  try {
    console.log('🔄 Fetching analytics...');
    setStatus('Loading analysis...', 'info');
    
    const response = await fetch(ANALYTICS_ENDPOINT);
    if (!response.ok) {
      setStatus('Failed to load data', 'error');
      return;
    }
    
    const data = await response.json();
    renderAnalytics(data);
  } catch (error) {
    console.error('❌ Error:', error);
    setStatus('Connection error: ' + error.message, 'error');
  }
}

async function syncGoogleSheets() {
  try {
    console.log('📤 Syncing from Google Sheets...');
    setStatus('⏳ Syncing fresh data from Google Sheets...', 'info');
    
    const response = await fetch(SYNC_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
                       getCookie('csrftoken')
      }
    });
    
    const data = await response.json();
    
    if (!response.ok || !data.success) {
      setStatus(`❌ Sync failed: ${data.error || 'Unknown error'}`, 'error');
      console.error('Sync error:', data);
      return;
    }
    
    console.log('✅ Sync successful:', data);
    setStatus(`✅ ${data.message}`, 'success');
    
    // Refresh charts after sync
    setTimeout(fetchAnalytics, 1000);
    
  } catch (error) {
    console.error('❌ Sync error:', error);
    setStatus('Sync failed: ' + error.message, 'error');
  }
}

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

function startPolling() {
  if (refreshTimer) clearInterval(refreshTimer);
  fetchAnalytics();
  refreshTimer = setInterval(fetchAnalytics, REFRESH_INTERVAL_MS);
}

if (refreshButton) {
  refreshButton.addEventListener('click', fetchAnalytics);
}

if (syncButton) {
  syncButton.addEventListener('click', syncGoogleSheets);
}

if (downloadButton) {
  downloadButton.addEventListener('click', () => {
    alert('Report download feature coming soon!');
  });
}

// =============================================================================
// 🆕 NEW: Hypothesis Testing Renderer (T-Test) - For Section 6
// =============================================================================
function renderHypothesisTests(ttest) {
  if (!ttest) return;
  
  const container = document.getElementById('hypothesisChart');
  if (!container) {
    console.error('❌ hypothesisChart div not found!');
    return;
  }
  
  const badge = ttest.significant 
    ? `<span class="badge success">✓ Significant (p < 0.05)</span>`
    : `<span class="badge warning">✗ Not Significant</span>`;
  
  container.innerHTML = `
    <div class="stats-card">
      <h4 style="margin:0 0 15px 0;color:#1e293b;">${ttest.test_type || 'T-Test'}</h4>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:15px;margin:15px 0;">
        <div class="stat-box" style="background:white;padding:12px;border-radius:8px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,0.1);">
          <strong style="color:#64748b;font-size:0.9em;">${ttest.groups_compared?.[0] || 'Group 1'}</strong>
          <div style="font-size:1.4em;font-weight:bold;color:#1e293b;margin:5px 0;">${typeof ttest.group1_mean === 'number' ? ttest.group1_mean.toFixed(2) : 'N/A'}</div>
          <div style="color:#64748b;font-size:0.85em;">n = ${ttest.sample_sizes?.group1 || '?'}</div>
        </div>
        <div class="stat-box" style="background:white;padding:12px;border-radius:8px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,0.1);">
          <strong style="color:#64748b;font-size:0.9em;">${ttest.groups_compared?.[1] || 'Group 2'}</strong>
          <div style="font-size:1.4em;font-weight:bold;color:#1e293b;margin:5px 0;">${typeof ttest.group2_mean === 'number' ? ttest.group2_mean.toFixed(2) : 'N/A'}</div>
          <div style="color:#64748b;font-size:0.85em;">n = ${ttest.sample_sizes?.group2 || '?'}</div>
        </div>
      </div>
      <div style="background:#f1f5f9;padding:8px 12px;border-radius:6px;font-family:monospace;font-size:0.9em;margin:10px 0;">
        t = ${typeof ttest.t_statistic === 'number' ? ttest.t_statistic.toFixed(4) : 'N/A'} | 
        p = ${typeof ttest.p_value === 'number' ? ttest.p_value.toFixed(4) : 'N/A'} | 
        d = ${typeof ttest.cohens_d === 'number' ? ttest.cohens_d.toFixed(3) : 'N/A'}
      </div>
      <div style="margin:10px 0;">${badge}</div>
      <p style="margin:0;color:#475569;font-size:0.95em;">${ttest.interpretation || ''}</p>
    </div>
  `;
}

// =============================================================================
// 🆕 NEW: Qualitative Insights Renderer (Sentiment + Frequencies) - For Section 7
// =============================================================================
function renderQualitativeInsights(qualData) {
  if (!qualData) return;
  
  // --- Sentiment Summary (Left Column) ---
  if (qualData.sentiment_summary && Object.keys(qualData.sentiment_summary).length > 0) {
    const container = document.getElementById('sentimentChart');
    if (!container) return;
    
    let html = '<h4 style="margin:0 0 15px 0;color:#1e293b;">📊 Perception Scores</h4><div style="display:grid;grid-template-columns:1fr;gap:10px;">';
    
    Object.entries(qualData.sentiment_summary).forEach(([question, data]) => {
      const colors = {
        'Very Positive': '#10b981', 'Positive': '#3b82f6', 'Neutral': '#f59e0b',
        'Negative': '#ef4444', 'Very Negative': '#dc2626'
      }[data.sentiment_label] || '#6b7280';
      
      const shortQ = question.length > 45 ? question.substring(0, 45) + '…' : question;
      
      html += `
        <div style="background:white;padding:12px;border-radius:8px;border-left:4px solid ${colors};box-shadow:0 1px 3px rgba(0,0,0,0.1);">
          <div style="font-size:0.85em;color:#1e293b;margin-bottom:8px;line-height:1.3;">${shortQ}</div>
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:1.3em;font-weight:bold;color:#1e293b;">${data.mean_score}/5</span>
            <span style="padding:4px 10px;border-radius:12px;background:${colors};color:white;font-size:0.75em;font-weight:500;">${data.sentiment_label}</span>
          </div>
          <div style="font-size:0.8em;color:#64748b;margin-top:5px;">${data.n_responses || 0} responses</div>
        </div>
      `;
    });
    
    html += '</div>';
    container.innerHTML = html;
  }
  
  // --- Frequency Distributions (Right Column) ---
  if (qualData.frequency_distributions && Object.keys(qualData.frequency_distributions).length > 0) {
    const container = document.getElementById('freqChart');
    if (!container) return;
    
    let html = '<h4 style="margin:0 0 15px 0;color:#1e293b;">📋 Response Frequencies</h4><div style="max-height:400px;overflow-y:auto;">';
    
    Object.entries(qualData.frequency_distributions).slice(0, 5).forEach(([col, data]) => {
      const shortCol = col.length > 35 ? col.substring(0, 35) + '…' : col;
      
      html += `<div style="background:white;padding:12px;border-radius:8px;margin-bottom:10px;box-shadow:0 1px 3px rgba(0,0,0,0.1);">
        <strong style="font-size:0.9em;color:#1e293b;">${shortCol}</strong>
        <table style="width:100%;font-size:0.8em;margin-top:8px;border-collapse:collapse;">
          <tr style="border-bottom:2px solid #e2e8f0;"><th style="text-align:left;padding:4px 0;color:#64748b;">Value</th><th style="text-align:center;padding:4px 0;color:#64748b;">Count</th><th style="text-align:right;padding:4px 0;color:#64748b;">%</th></tr>`;
      
      Object.entries(data.frequencies).slice(0, 4).forEach(([val, count]) => {
        const pct = data.percentages?.[val] || 0;
        html += `<tr style="border-bottom:1px solid #f1f5f9;"><td style="padding:4px 0;">${val}</td><td style="text-align:center;padding:4px 0;font-weight:500;">${count}</td><td style="text-align:right;padding:4px 0;color:#64748b;">${pct}%</td></tr>`;
      });
      
      html += '</table></div>';
    });
    
    html += '</div>';
    container.innerHTML = html;
  }
}

// =============================================================================
// 🆕 NEW: Update Footer Metadata
// =============================================================================
function updateAnalysisMetadata(metadata) {
  const footer = document.getElementById('analysisFooter');
  if (!footer) return;
  
  footer.innerHTML = `<small style="color:#64748b;">📊 ${metadata.quantitative_vars || 0} quantitative + ${metadata.qualitative_vars || 0} qualitative | 📥 ${metadata.total_responses || 0} responses | 🕐 ${new Date(metadata.analysis_timestamp).toLocaleTimeString()}</small>`;
}

window.addEventListener('DOMContentLoaded', startPolling);

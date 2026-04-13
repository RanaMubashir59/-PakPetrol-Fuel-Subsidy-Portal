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

window.addEventListener('DOMContentLoaded', startPolling);

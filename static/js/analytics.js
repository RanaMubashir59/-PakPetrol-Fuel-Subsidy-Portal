const ANALYTICS_ENDPOINT = '/analytics/data/';
const REFRESH_INTERVAL_MS = 10000;
let refreshTimer = null;

const statusEl = document.getElementById('analyticsStatus');
const lastUpdatedEl = document.getElementById('lastUpdated');
const refreshButton = document.getElementById('refreshButton');
const chartsContainer = document.getElementById('charts');

function setStatus(message, type = 'info') {
  if (!statusEl) return;
  statusEl.textContent = message;
  statusEl.className = `status ${type}`;
}

function setLastUpdated(timestamp) {
  if (!lastUpdatedEl) return;
  lastUpdatedEl.textContent = `Last updated: ${timestamp}`;
}

function ensureChartDiv(id, title) {
  let container = document.getElementById(id);
  if (!container) {
    container = document.createElement('div');
    container.id = id;
    container.className = 'chart-card';
    if (title) {
      const header = document.createElement('h2');
      header.textContent = title;
      container.appendChild(header);
    }
    chartsContainer.appendChild(container);
  }
  return container;
}

function renderDescriptiveStats(stats) {
  const container = ensureChartDiv('descriptiveStatsChart', 'Descriptive Statistics');
  container.innerHTML = '<h2>Descriptive Statistics Summary</h2><div id="statsTable"></div>';
  
  const statsTable = document.getElementById('statsTable');
  statsTable.style.overflowX = 'auto';
  
  let html = '<table style="width:100%; border-collapse: collapse; font-size: 12px;">';
  html += '<tr style="background: #e3f2fd;"><th style="border: 1px solid #ccc; padding: 8px; text-align: left;"><strong>Variable</strong></th>';
  html += '<th style="border: 1px solid #ccc; padding: 8px;">Count</th>';
  html += '<th style="border: 1px solid #ccc; padding: 8px;">Mean</th>';
  html += '<th style="border: 1px solid #ccc; padding: 8px;">Median</th>';
  html += '<th style="border: 1px solid #ccc; padding: 8px;">Std Dev</th>';
  html += '<th style="border: 1px solid #ccc; padding: 8px;">Min</th>';
  html += '<th style="border: 1px solid #ccc; padding: 8px;">Max</th></tr>';
  
  Object.entries(stats).forEach(([varName, stats_obj]) => {
    if (stats_obj && stats_obj.count > 0) {
      html += `<tr style="background: #fff;">`;
      html += `<td style="border: 1px solid #ddd; padding: 8px;"><strong>${varName.substring(0, 25)}</strong></td>`;
      html += `<td style="border: 1px solid #ddd; padding: 8px; text-align: center;">${stats_obj.count}</td>`;
      html += `<td style="border: 1px solid #ddd; padding: 8px; text-align: center;">${stats_obj.mean?.toFixed(2) || 'N/A'}</td>`;
      html += `<td style="border: 1px solid #ddd; padding: 8px; text-align: center;">${stats_obj.median?.toFixed(2) || 'N/A'}</td>`;
      html += `<td style="border: 1px solid #ddd; padding: 8px; text-align: center;">${stats_obj.std_dev?.toFixed(2) || 'N/A'}</td>`;
      html += `<td style="border: 1px solid #ddd; padding: 8px; text-align: center;">${stats_obj.min?.toFixed(2) || 'N/A'}</td>`;
      html += `<td style="border: 1px solid #ddd; padding: 8px; text-align: center;">${stats_obj.max?.toFixed(2) || 'N/A'}</td>`;
      html += `</tr>`;
    }
  });
  
  html += '</table>';
  statsTable.innerHTML = html;
}

function renderDemographics(demographics) {
  const wrapper = ensureChartDiv('demographicsCharts', 'Demographics Analysis');
  wrapper.innerHTML = '<h2>Demographics</h2>';

  Object.keys(demographics).forEach((question) => {
    const data = demographics[question];
    if (!data || Object.keys(data).length === 0) return;
    
    const questionId = `demo_${question.replace(/[^a-zA-Z0-9]/g, '_')}`;
    let card = document.getElementById(questionId);
    if (!card) {
      card = document.createElement('div');
      card.id = questionId;
      card.className = 'chart-card';
      wrapper.appendChild(card);
    }
    card.innerHTML = `<h3>${question}</h3><div id="${questionId}_plot"></div>`;

    const categories = Object.keys(data);
    const values = Object.values(data);

    Plotly.react(`${questionId}_plot`, [
      {
        type: 'bar',
        x: categories,
        y: values,
        marker: { color: '#3b82f6' },
      },
    ], {
      margin: { t: 30, b: 100 },
      xaxis: { automargin: true },
      yaxis: { title: 'Count' },
    });
  });
}

function renderRegression(regression) {
  if (!regression || !regression.x || regression.x.length === 0) {
    console.warn('⚠️ Regression data unavailable');
    return;
  }
  
  const container = ensureChartDiv('regressionChart', 'Regression Analysis');
  container.innerHTML = `<h2>${regression.title || 'Regression Analysis'}</h2><div id="regressionPlot"></div>`;

  const x = regression.x;
  const y = regression.y;
  const lineY = regression.x_line.map((val, i) => regression.slope * val + regression.intercept);

  Plotly.react('regressionPlot', [
    {
      x,
      y,
      mode: 'markers',
      type: 'scatter',
      name: 'Data points',
      marker: { color: '#22c55e', size: 8, opacity: 0.8 },
    },
    {
      x: regression.x_line || x.sort((a,b) => a-b),
      y: lineY,
      mode: 'lines',
      type: 'scatter',
      name: 'Fit line',
      line: { color: '#ef4444', width: 3 },
    },
  ], {
    margin: { t: 30, b: 80 },
    xaxis: { title: regression.x_label || 'X Variable', automargin: true },
    yaxis: { title: regression.y_label || 'Y Variable', automargin: true },
    showlegend: true,
  });
  
  // Add statistics panel
  const statsEl = document.createElement('div');
  statsEl.style.cssText = 'margin-top: 15px; padding: 12px; background: #f0f4f8; border-radius: 6px; font-size: 12px;';
  statsEl.innerHTML = `
    <div style="margin-bottom: 8px;"><strong>Regression Equation:</strong> ${regression.equation}</div>
    <div style="margin-bottom: 8px;"><strong>R² Value:</strong> ${regression.r_squared.toFixed(4)} (${(regression.r_squared*100).toFixed(1)}% variance explained)</div>
    <div style="margin-bottom: 8px;"><strong>Pearson r:</strong> ${regression.r_value.toFixed(4)}</div>
    <div style="margin-bottom: 8px;"><strong>p-value:</strong> ${regression.p_value.toFixed(4)} - <span style="color: ${regression.p_value < 0.05 ? '#10b981' : '#f59e0b'};"><strong>${regression.significance}</strong></span></div>
    <div><strong>n =</strong> ${regression.n_samples}</div>
  `;
  container.appendChild(statsEl);
}

function renderCorrelations(correlations) {
  if (!correlations || Object.keys(correlations).length === 0) {
    console.warn('⚠️ Correlation data unavailable');
    return;
  }
  
  const container = ensureChartDiv('correlationChart', 'Correlation Analysis (Pearson r)');
  container.innerHTML = '<h2>Correlation Analysis</h2><div id="correlationTable"></div>';
  
  const corrTable = document.getElementById('correlationTable');
  corrTable.style.overflowX = 'auto';
  
  let html = '<table style="width:100%; border-collapse: collapse; font-size: 12px;">';
  html += '<tr style="background: #f3e5f5;"><th style="border: 1px solid #ccc; padding: 8px; text-align: left;"><strong>Variables</strong></th>';
  html += '<th style="border: 1px solid #ccc; padding: 8px;">Pearson r</th>';
  html += '<th style="border: 1px solid #ccc; padding: 8px;">Strength</th>';
  html += '<th style="border: 1px solid #ccc; padding: 8px;">p-value</th>';
  html += '<th style="border: 1px solid #ccc; padding: 8px;">Sig.</th></tr>';
  
  Object.entries(correlations).forEach(([pair, corrData]) => {
    if (corrData) {
      const sigColor = corrData.p_value < 0.05 ? '#10b981' : '#f59e0b';
      html += `<tr style="background: #fff;">`;
      html += `<td style="border: 1px solid #ddd; padding: 8px;"><strong>${pair}</strong></td>`;
      html += `<td style="border: 1px solid #ddd; padding: 8px; text-align: center;"><strong>${corrData.pearson_r.toFixed(4)}</strong></td>`;
      html += `<td style="border: 1px solid #ddd; padding: 8px; text-align: center;">${corrData.strength}</td>`;
      html += `<td style="border: 1px solid #ddd; padding: 8px; text-align: center;">${corrData.p_value.toFixed(4)}</td>`;
      html += `<td style="border: 1px solid #ddd; padding: 8px; text-align: center; color: ${sigColor};"><strong>${corrData.p_value < 0.05 ? 'Yes' : 'No'}</strong></td>`;
      html += `</tr>`;
    }
  });
  
  html += '</table>';
  corrTable.innerHTML = html;
}

function renderANOVA(anova) {
  if (!anova || !anova.f_statistic) {
    console.warn('⚠️ ANOVA data unavailable');
    return;
  }
  
  const container = ensureChartDiv('anovaChart', 'ANOVA Analysis');
  container.innerHTML = `<h2>${anova.title || 'ANOVA - Analysis of Variance'}</h2><div id="anovaPlot"></div>`;
  
  // Create box plot for group comparison
  const traces = anova.groups.map((groupName, i) => ({
    y: [anova.group_means[groupName]],
    name: groupName,
    type: 'bar',
    error_y: {
      type: 'data',
      array: [anova.group_stds[groupName]],
      visible: true
    }
  }));
  
  Plotly.react('anovaPlot', traces, {
    margin: { t: 30, b: 80 },
    xaxis: { title: 'Groups' },
    yaxis: { title: 'Mean Score' },
    showlegend: true,
  });
  
  // Add ANOVA statistics
  const statsEl = document.createElement('div');
  statsEl.style.cssText = 'margin-top: 15px; padding: 12px; background: #fef3c7; border-radius: 6px; font-size: 12px;';
  statsEl.innerHTML = `
    <div style="margin-bottom: 8px;"><strong>F-Statistic:</strong> ${anova.f_statistic.toFixed(4)}</div>
    <div style="margin-bottom: 8px;"><strong>p-value:</strong> ${anova.p_value.toFixed(4)}</div>
    <div style="color: ${anova.p_value < 0.05 ? '#10b981' : '#ef4444'};"><strong>${anova.significance}</strong></div>
  `;
  container.appendChild(statsEl);
}

function renderChiSquare(chiSquareData) {
  const container = ensureChartDiv('chiSquareCharts', 'Chi-Square Tests');
  container.innerHTML = '<h2>Chi-Square Independence Tests</h2>';

  Object.keys(chiSquareData).forEach((groupCol) => {
    const blockId = `chi_${groupCol.replace(/[^a-zA-Z0-9]/g,'_')}`;
    let block = document.getElementById(blockId);
    if (!block) {
      block = document.createElement('div');
      block.id = blockId;
      block.className = 'chart-card';
      container.appendChild(block);
    }

    const chartId = `${blockId}_plot`;
    block.innerHTML = `<h3>${chiSquareData[groupCol].title || groupCol}</h3><div id="${chartId}"></div>`;
    
    try {
      const chartData = chiSquareData[groupCol];
      if (!chartData || !chartData.contingency) return;
      
      const contingency = chartData.contingency;
      const rows = Object.keys(contingency);
      const cols = rows.length > 0 ? Object.keys(contingency[rows[0]] || {}) : [];
      
      if (rows.length === 0 || cols.length === 0) {
        block.innerHTML += '<p>No data available</p>';
        return;
      }
      
      const z = rows.map((row) => cols.map((col) => contingency[row]?.[col] || 0));

      Plotly.react(chartId, [
        {
          z,
          x: cols,
          y: rows,
          type: 'heatmap',
          colorscale: 'Blues',
        },
      ], {
        margin: { t: 30, b: 100, l: 100 },
        xaxis: { automargin: true },
        yaxis: { automargin: true },
      });

      const statsEl = document.createElement('div');
      statsEl.innerHTML = `<p style="font-size: 11px; color: #333; margin-top: 8px; background: #e8f5e9; padding: 8px; border-radius: 4px;">
        <strong>χ²:</strong> ${chartData.chi2.toFixed(3)} | 
        <strong>p-value:</strong> ${chartData.p_value.toFixed(4)} | 
        <strong>dof:</strong> ${chartData.dof} | 
        <strong>Result:</strong> <span style="color: ${chartData.p_value < 0.05 ? '#10b981' : '#f59e0b'};"><strong>${chartData.p_value < 0.05 ? 'Significant' : 'Not Significant'}</strong></span>
      </p>`;
      block.appendChild(statsEl);
    } catch (e) {
      console.error('Error rendering chi-square for', groupCol, e);
      block.innerHTML += '<p>Error rendering chart</p>';
    }
  });
}

function renderAnalytics(data) {
  if (data.error) {
    setStatus(data.error, 'error');
    console.error('❌ API Error:', data.error);
    return;
  }

  setStatus('✅ Data loaded and comprehensive statistical analysis complete.', 'success');
  setLastUpdated(new Date(data.generated_at).toLocaleString());

  console.log('📊 Rendering all statistical sections:', {
    descriptive_stats: Object.keys(data.descriptive_stats || {}).length,
    demographics: Object.keys(data.demographics || {}).length,
    regression: !!data.regression?.equation,
    correlations: Object.keys(data.correlations || {}).length,
    anova: !!data.anova?.f_statistic,
    chi_square: Object.keys(data.chi_square || {}).length,
    awareness: !!data.awareness,
    subsidy_perception: !!data.subsidy_perception,
  });

  // Render in order: stats first, then visualizations
  if (data.descriptive_stats) renderDescriptiveStats(data.descriptive_stats);
  if (data.demographics) renderDemographics(data.demographics);
  if (data.regression) renderRegression(data.regression);
  if (data.correlations && Object.keys(data.correlations).length > 0) renderCorrelations(data.correlations);
  if (data.anova) renderANOVA(data.anova);
  if (data.chi_square && Object.keys(data.chi_square).length > 0) renderChiSquare(data.chi_square);
  if (data.awareness) renderAwareness(data.awareness);
  if (data.subsidy_perception) renderSubsidyPerception(data.subsidy_perception);
}

async function fetchAnalytics() {
  try {
    console.log('🔄 Fetching analytics from:', ANALYTICS_ENDPOINT);
    setStatus('Loading data...', 'info');
    
    const response = await fetch(ANALYTICS_ENDPOINT);
    console.log('📡 Response status:', response.status);
    
    if (!response.ok) {
      try {
        const payload = await response.json();
        console.error('❌ API Error:', payload);
        setStatus(payload.error || 'Failed to load analytics data.', 'error');
      } catch {
        setStatus('Failed to load analytics data (HTTP ' + response.status + ')', 'error');
      }
      return;
    }
    
    const payload = await response.json();
    console.log('✅ Full payload received:', payload);
    
    renderAnalytics(payload);
  } catch (error) {
    console.error('❌ Error fetching analytics:', error);
    setStatus('Unable to connect to analytics endpoint: ' + error.message, 'error');
  }
}

function startPolling() {
  if (refreshTimer) {
    clearInterval(refreshTimer);
  }
  console.log('📊 Starting auto-refresh polling every', REFRESH_INTERVAL_MS, 'ms');
  fetchAnalytics(); // Fetch immediately on start
  refreshTimer = setInterval(fetchAnalytics, REFRESH_INTERVAL_MS);
}

if (refreshButton) {
  refreshButton.addEventListener('click', () => {
    console.log('🔵 Manual refresh clicked');
    fetchAnalytics();
  });
}

window.addEventListener('DOMContentLoaded', () => {
  console.log('📄 DOM loaded, initializing analytics dashboard');
  startPolling();
});

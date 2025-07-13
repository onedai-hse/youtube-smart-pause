// YouTube Smart Pause Extension - Content Script
console.log('YouTube Assistant: Content script loaded successfully.');

let sidebarOpen = false;
let updateInterval = null;
let lastUpdateTime = 0;
let lastVideoTime = 0;

function getVideoId() {
  const url = window.location.href;
  const match = url.match(/[?&]v=([^&]+)/);
  return match ? match[1] : null;
}

function createSidebar() {
  const sidebar = document.createElement('div');
  sidebar.id = 'youtube-assistant-sidebar';
  sidebar.innerHTML = `
    <div class="sidebar-header">
      <h3>YouTube Smart Pause</h3>
      <button id="close-sidebar" title="Close sidebar">×</button>
    </div>
    <div class="sidebar-content">
      <div class="section">
        <h4>📹 Current Video</h4>
        <div id="assistant-video-info">Loading...</div>
      </div>
      <div class="section">
        <h4>🎯 Statement to Analyze</h4>
        <div id="statement-to-analyze">Extracting statement...</div>
      </div>
      <div class="section">
        <button id="analyze-current">
          <span class="button-text">Analyze Statement</span>
          <span class="button-loading" style="display: none;">Analyzing...</span>
        </button>
      </div>
      <div class="section">
        <h4>Analysis Result</h4>
        <div id="analysis-result">Press "Analyze Statement" to start</div>
      </div>
    </div>
  `;
  
  document.body.appendChild(sidebar);
  document.getElementById('close-sidebar').addEventListener('click', closeSidebar);
  document.getElementById('analyze-current').addEventListener('click', analyzeCurrentPosition);
  return sidebar;
}

function getVideoTitle() {
  // Try multiple selectors to get the video title
  const titleSelectors = [
    'h1.title.style-scope.ytd-video-primary-info-renderer',
    'h1.ytd-video-primary-info-renderer', 
    'h1[class*="title"]',
    'ytd-video-primary-info-renderer h1',
    '.title.style-scope.ytd-video-primary-info-renderer'
  ];
  
  for (const selector of titleSelectors) {
    const titleElement = document.querySelector(selector);
    if (titleElement) {
      return titleElement.textContent.trim();
    }
  }
  
  return 'Video title not found';
}

async function extractStatementToAnalyze(videoId, currentTime) {
  try {
    const response = await fetch(`http://localhost:8000/transcript/${videoId}?start_time=${currentTime}&duration=30`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });
    
    if (!response.ok) {
      return 'Statement extraction failed';
    }
    
    const data = await response.json();
    
    // Use the filtered fact that would actually be analyzed
    if (data.will_analyze && data.will_analyze !== 'No extractable fact found') {
      return data.will_analyze;
    }
    
    return 'No extractable statement found in current segment';
  } catch (error) {
    return 'Error extracting statement';
  }
}

// Store the current statement to analyze
let currentStatementToAnalyze = null;

async function updateVideoInfo() {
  const video = document.querySelector('video');
  const videoInfo = document.getElementById('assistant-video-info');
  
  if (!videoInfo) return;
  
  if (!video) {
    videoInfo.innerHTML = '<p>❌ Video not detected</p>';
    return;
  }
  
  if (video.duration && !isNaN(video.duration)) {
    const currentTime = Math.floor(video.currentTime);
    const duration = Math.floor(video.duration);
    const progress = ((currentTime / duration) * 100).toFixed(1);
    const videoTitle = getVideoTitle();
    
    videoInfo.innerHTML = `
      <div style="margin-bottom: 12px;">
        <h4 style="
          margin: 0 0 8px 0;
          font-size: 14px;
          font-weight: 600;
          color: #fff;
          line-height: 1.3;
          opacity: 0.9;
        ">${videoTitle}</h4>
        <p style="
          margin: 0 0 8px 0;
          font-size: 12px;
          color: #fff;
          opacity: 0.7;
        ">Time: ${formatTime(currentTime)} / ${formatTime(duration)} (${progress}%)</p>
        <p style="
          margin: 0;
          font-size: 12px;
          color: #fff;
          opacity: 0.7;
        ">${video.paused ? '⏸️ Paused' : '▶️ Playing'}</p>
      </div>
    `;
  } else {
    videoInfo.innerHTML = '<p>Video loading...</p>';
  }
}

async function updateStatementToAnalyze() {
  const video = document.querySelector('video');
  const statementDiv = document.getElementById('statement-to-analyze');
  
  if (!statementDiv || !video) return;
  
  const videoId = getVideoId();
  const currentTime = Math.floor(video.currentTime);
  
  // Extract the statement
  const statement = await extractStatementToAnalyze(videoId, currentTime);
  currentStatementToAnalyze = statement;
  
  // Display the statement
  if (statement === 'No extractable statement found in current segment' || 
      statement === 'Error extracting statement' || 
      statement === 'Statement extraction failed') {
    statementDiv.innerHTML = `
      <div style="
        background: rgba(255, 152, 0, 0.2);
        border-radius: 8px;
        padding: 12px;
        border-left: 3px solid #ff9500;
      ">
        <p style="
          margin: 0;
          font-size: 13px;
          color: #ff9500;
          font-weight: 500;
        ">${statement}</p>
      </div>
    `;
  } else {
    statementDiv.innerHTML = `
      <div style="
        background: rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        padding: 12px;
        border-left: 3px solid #007aff;
      ">
        <p style="
          margin: 0;
          font-size: 13px;
          line-height: 1.4;
          color: #fff;
          opacity: 0.9;
          font-style: italic;
        ">"${statement}"</p>
      </div>
    `;
  }
}

function formatTime(seconds) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  
  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

function showSidebar() {
  if (sidebarOpen) return;
  
  const sidebar = createSidebar();
  
  // Добавляем небольшую задержку для плавной анимации
  setTimeout(() => {
    sidebar.classList.add('sidebar-open');
  }, 10);
  
  sidebarOpen = true;
  
  // Update video info and extract statement immediately
  updateVideoInfo();
  updateStatementToAnalyze();
  
  // Only update video info periodically, statement is extracted once on sidebar open
  updateInterval = setInterval(updateVideoInfo, 2000);
}

function closeSidebar() {
  const sidebar = document.getElementById('youtube-assistant-sidebar');
  if (sidebar) {
    sidebar.classList.remove('sidebar-open');
    
    // Ждем окончания анимации перед удалением
    setTimeout(() => {
      sidebar.remove();
      sidebarOpen = false;
      if (updateInterval) {
        clearInterval(updateInterval);
        updateInterval = null;
      }
    }, 400);
  }
}

function createVerdictBadge(decision) {
  const badgeStyles = {
    'true': { color: '#fff', bg: '#34c759', icon: '✓', text: 'TRUE' },
    'false': { color: '#fff', bg: '#ff3b30', icon: '✗', text: 'FALSE' },
    'unknown': { color: '#fff', bg: '#ff9500', icon: '?', text: 'UNCLEAR' }
  };
  
  const style = badgeStyles[decision.toLowerCase()] || badgeStyles['unknown'];
  
  return `
    <div style="
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 8px 12px;
      background: ${style.bg};
      color: ${style.color};
      border-radius: 20px;
      font-size: 14px;
      font-weight: 600;
      margin-bottom: 16px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    ">
      <span style="font-size: 16px;">${style.icon}</span>
      <span>${style.text}</span>
    </div>
  `;
}

function createSourcesCard(sources) {
  if (!sources || sources.length === 0) {
    return '';
  }
  
  const sourcesList = sources.map(source => `
    <div style="margin-bottom: 8px;">
      <a href="${source}" target="_blank" style="
        color: #007aff;
        text-decoration: none;
        font-size: 14px;
        line-height: 1.4;
        display: block;
        word-break: break-all;
      " onmouseover="this.style.textDecoration='underline'" onmouseout="this.style.textDecoration='none'">
        🔗 ${source}
      </a>
    </div>
  `).join('');
  
  return `
    <div style="
      background: rgba(255, 255, 255, 0.1);
      border-radius: 12px;
      padding: 16px;
      margin-top: 16px;
      border: 1px solid rgba(255, 255, 255, 0.2);
    ">
      <h5 style="
        margin: 0 0 12px 0;
        font-size: 14px;
        font-weight: 600;
        color: #fff;
        opacity: 0.9;
      ">📚 Sources</h5>
      <div>${sourcesList}</div>
    </div>
  `;
}

async function analyzeCurrentPosition() {
  const resultDiv = document.getElementById('analysis-result');
  const button = document.getElementById('analyze-current');
  const buttonText = button.querySelector('.button-text');
  const buttonLoading = button.querySelector('.button-loading');
  const video = document.querySelector('video');
  
  if (!video) {
    resultDiv.innerHTML = '<p>❌ Video not found</p>';
    return;
  }
  
  // Check if we have a statement to analyze
  if (!currentStatementToAnalyze || 
      currentStatementToAnalyze === 'No extractable statement found in current segment' ||
      currentStatementToAnalyze === 'Error extracting statement' ||
      currentStatementToAnalyze === 'Statement extraction failed') {
    resultDiv.innerHTML = `
      <div style="
        padding: 16px;
        background: rgba(255, 152, 0, 0.2);
        border-radius: 8px;
        border: 1px solid rgba(255, 152, 0, 0.3);
      ">
        <p style="
          margin: 0;
          color: #ff9500;
          font-size: 14px;
          font-weight: 500;
        ">⚠️ No statement available for analysis</p>
      </div>
    `;
    return;
  }
  
  // Показываем состояние загрузки
  buttonText.style.display = 'none';
  buttonLoading.style.display = 'inline';
  button.disabled = true;
  resultDiv.innerHTML = '<p>Analyzing statement...</p>';
  
  // Use the fact-check endpoint with the already extracted statement
  const requestData = {
    statement: currentStatementToAnalyze
  };
  
  try {
    const response = await fetch('http://localhost:8000/fact-check', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestData)
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Server error: ${response.status} - ${errorText}`);
    }

    const data = await response.json();
    
    // Handle structured response
    if (data.fact_check) {
      const verdictBadge = createVerdictBadge(data.fact_check.final_decision);
      const sourcesCard = createSourcesCard(data.fact_check.sources);
      
      resultDiv.innerHTML = `
        <div style="color: #fff;">
          ${verdictBadge}
          
          <div style="margin-bottom: 16px;">
            <h5 style="
              margin: 0 0 8px 0;
              font-size: 14px;
              font-weight: 600;
              color: #fff;
              opacity: 0.9;
            ">📝 Analysis</h5>
            <p style="
              margin: 0;
              font-size: 14px;
              line-height: 1.5;
              color: #fff;
              opacity: 0.9;
            ">${data.fact_check.short_explanation}</p>
          </div>
          
          ${sourcesCard}
          
          <div style="
            margin-top: 16px;
            padding: 8px;
            background: rgba(52, 199, 89, 0.2);
            border-radius: 8px;
            border: 1px solid rgba(52, 199, 89, 0.3);
          ">
            <p style="
              margin: 0;
              font-size: 12px;
              color: #34c759;
              text-align: center;
              font-weight: 500;
            ">✅ Analysis completed successfully!</p>
          </div>
        </div>
      `;
    } else {
      throw new Error('Invalid response format from API');
    }
    
  } catch (error) {
    resultDiv.innerHTML = `
      <div style="
        padding: 16px;
        background: rgba(255, 59, 48, 0.2);
        border-radius: 8px;
        border: 1px solid rgba(255, 59, 48, 0.3);
      ">
        <p style="
          margin: 0;
          color: #ff3b30;
          font-size: 14px;
          font-weight: 500;
        ">❌ Error: ${error.message}</p>
      </div>
    `;
  } finally {
    // Восстанавливаем кнопку
    buttonText.style.display = 'inline';
    buttonLoading.style.display = 'none';
    button.disabled = false;
  }
}

// Улучшенная обработка клавиш с предотвращением конфликтов
document.addEventListener('keydown', function(event) {
  // Проверяем, что пользователь не вводит текст в поле ввода
  const activeElement = document.activeElement;
  const isInputField = activeElement && (
    activeElement.tagName === 'INPUT' || 
    activeElement.tagName === 'TEXTAREA' || 
    activeElement.contentEditable === 'true'
  );
  
  if (event.code === 'KeyE' && !isInputField && !event.ctrlKey && !event.metaKey) {
    event.preventDefault();
    if (sidebarOpen) {
      closeSidebar();
    } else {
      showSidebar();
    }
  }
});

function handlePause() {
  if (sidebarOpen) {
    updateVideoInfo();
  }
}

// Инициализация при загрузке страницы
function initializeExtension() {
  const video = document.querySelector('video');
  if (video) {
    video.addEventListener('pause', handlePause);
    video.addEventListener('play', handlePause);
  }
  
  // Добавляем обработчик для динамически загружаемых видео
  const observer = new MutationObserver(function(mutations) {
    mutations.forEach(function(mutation) {
      mutation.addedNodes.forEach(function(node) {
        if (node.nodeType === 1 && node.tagName === 'VIDEO') {
          node.addEventListener('pause', handlePause);
          node.addEventListener('play', handlePause);
        }
      });
    });
  });
  
  observer.observe(document.body, {
    childList: true,
    subtree: true
  });
}

// Запускаем инициализацию после загрузки DOM
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeExtension);
} else {
  initializeExtension();
}
if (typeof marked === 'function') {
  console.log('YouTube Assistant: marked.js library loaded successfully.');
} else {
  console.error('YouTube Assistant: marked.js library NOT FOUND. Markdown will not be rendered. Please ensure marked.min.js is in the browser_extention folder.');
}

let sidebarOpen = false;
let updateInterval = null;

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
        <button id="analyze-current">
          <span class="button-text">Analyze Current Position</span>
          <span class="button-loading" style="display: none;">Analyzing...</span>
        </button>
      </div>
      <div class="section">
        <h4>Analysis Result</h4>
        <div id="analysis-result">Press "Analyze" to start</div>
      </div>
    </div>
  `;
  
  document.body.appendChild(sidebar);
  document.getElementById('close-sidebar').addEventListener('click', closeSidebar);
  document.getElementById('analyze-current').addEventListener('click', analyzeCurrentPosition);
  return sidebar;
}

function updateVideoInfo() {
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
    const videoId = getVideoId();
    const progress = ((currentTime / duration) * 100).toFixed(1);
    
    videoInfo.innerHTML = `
      <p>Time: ${formatTime(currentTime)} / ${formatTime(duration)} (${progress}%)</p>
      <p>Video ID: ${videoId || 'Not found'}</p>
      <p>${video.paused ? 'Paused' : 'Playing'}</p>
    `;
  } else {
    videoInfo.innerHTML = '<p>Video loading...</p>';
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
  
  updateVideoInfo();
  updateInterval = setInterval(updateVideoInfo, 1000);
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
  
  // Показываем состояние загрузки
  buttonText.style.display = 'none';
  buttonLoading.style.display = 'inline';
  button.disabled = true;
  resultDiv.innerHTML = '<p>Analyzing video content...</p>';
  
  const requestData = {
    video_id: getVideoId(),
    current_time: video.currentTime,
    context_seconds: 30
  };
  
  try {
    const response = await fetch('http://localhost:8000/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestData)
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Server error: ${response.status} - ${errorText}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    resultDiv.innerHTML = ''; // Clear "Analyzing..."
    let fullText = '';
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }
      const chunk = decoder.decode(value, { stream: true });
      fullText += chunk;
      if (typeof marked === 'function') {
        resultDiv.innerHTML = marked.parse(fullText);
      } else {
        resultDiv.textContent = fullText; // Fallback if marked.js is not loaded
      }
    }
    
    // Добавляем успешное завершение
    resultDiv.innerHTML += '<p style="color: #34c759; margin-top: 16px;">Analysis completed successfully!</p>';
    
  } catch (error) {
    resultDiv.innerHTML = `<p>❌ Error: ${error.message}</p>`;
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
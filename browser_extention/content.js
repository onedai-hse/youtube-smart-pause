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
      <h3>YouTube Assistant</h3>
      <button id="close-sidebar">×</button>
    </div>
    <div class="sidebar-content">
      <div class="section">
        <h4>Current Video</h4>
        <div id="assistant-video-info">Loading...</div>
      </div>
      <div class="section">
        <button id="analyze-current">Analyze Current Position</button>
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
    videoInfo.innerHTML = '<p>Video not detected</p>';
    return;
  }
  
  if (video.duration && !isNaN(video.duration)) {
    const currentTime = Math.floor(video.currentTime);
    const duration = Math.floor(video.duration);
    const videoId = getVideoId();
    
    videoInfo.innerHTML = `
      <p>Time: ${currentTime}s / ${duration}s</p>
      <p>Video ID: ${videoId || 'Not found'}</p>
      <p>Status: ${video.paused ? 'Paused' : 'Playing'}</p>
    `;
  } else {
    videoInfo.innerHTML = '<p>Video loading...</p>';
  }
}

function showSidebar() {
  if (sidebarOpen) return;
  
  const sidebar = createSidebar();
  sidebar.classList.add('sidebar-open');
  sidebarOpen = true;
  
  updateVideoInfo();
  updateInterval = setInterval(updateVideoInfo, 1000);
}

function closeSidebar() {
  const sidebar = document.getElementById('youtube-assistant-sidebar');
  if (sidebar) {
    sidebar.remove();
    sidebarOpen = false;
    if (updateInterval) {
      clearInterval(updateInterval);
      updateInterval = null;
    }
  }
}

function analyzeCurrentPosition() {
  const resultDiv = document.getElementById('analysis-result');
  const video = document.querySelector('video');
  
  if (!video) {
    resultDiv.textContent = 'Video not found';
    return;
  }
  
  resultDiv.textContent = 'Analyzing...';
  
  const requestData = {
    video_id: getVideoId(),
    current_time: video.currentTime,
    context_seconds: 30
  };
  
  fetch('http://localhost:5000/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(requestData)
  })
  .then(response => response.json())
  .then(result => {
    resultDiv.textContent = result.analysis || 'Analysis completed';
  })
  .catch(error => {
    resultDiv.textContent = 'Error: ' + error.message;
  });
}

document.addEventListener('keydown', function(event) {
  if (event.code === 'KeyE') {
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

const video = document.querySelector('video');
if (video) {
  video.addEventListener('pause', handlePause);
}
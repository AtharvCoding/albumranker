// rank_result.js - Handle save, export functionality

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

// Save button handler
if (document.getElementById('save-btn')) {
  const saveBtn = document.getElementById('save-btn');
  saveBtn.addEventListener('click', async () => {
    const token = csrfToken || getCookie('csrftoken');
    if (saved) {
      // Unsave
      try {
        const response = await fetch(`/api/unsave-album/${albumId}/`, {
          method: 'POST',
          headers: {
            'X-CSRFToken': token,
            'Content-Type': 'application/json',
          },
        });
        if (response.ok) {
          saveBtn.textContent = 'Save to My Music';
          saveBtn.style.background = '#111';
          window.saved = false;
        }
      } catch (e) {
        alert('Error unsaving album');
      }
    } else {
      // Save with ranking data
      try {
        const response = await fetch(`/api/save-album/${albumId}/`, {
          method: 'POST',
          headers: {
            'X-CSRFToken': token,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            ordered_ids: orderedIds,
            comparisons_count: comparisonsCount,
          }),
        });
        if (response.ok) {
          const data = await response.json();
          if (data.success) {
            saveBtn.textContent = '✓ Saved';
            saveBtn.style.background = '#10b981';
            window.saved = true;
          }
        }
      } catch (e) {
        alert('Error saving album');
      }
    }
  });
}

// Export menu toggle
const exportBtn = document.getElementById('export-btn');
const exportMenu = document.getElementById('export-menu');
if (exportBtn && exportMenu) {
  exportBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    exportMenu.style.display = exportMenu.style.display === 'none' ? 'block' : 'none';
  });
  
  document.addEventListener('click', () => {
    exportMenu.style.display = 'none';
  });
  
  exportMenu.addEventListener('click', (e) => {
    e.stopPropagation();
  });
}

// Export CSV
if (document.getElementById('export-csv')) {
  document.getElementById('export-csv').addEventListener('click', () => {
    const csvRows = ['Rank,Track Name,Duration (ms),Track Number'];
    tracks.forEach((track, index) => {
      const rank = index + 1;
      csvRows.push(`${rank},"${track.name.replace(/"/g, '""')}",${track.duration_ms},${track.track_number}`);
    });
    
    const csvContent = csvRows.join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${albumName.replace(/[^a-z0-9]/gi, '_')}_ranking.csv`;
    link.click();
    URL.revokeObjectURL(url);
    exportMenu.style.display = 'none';
  });
}

// Export PNG
if (document.getElementById('export-png')) {
  document.getElementById('export-png').addEventListener('click', async () => {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    
    // Set canvas size
    const padding = 40;
    const lineHeight = 30;
    const headerHeight = 200;
    const trackListHeight = tracks.length * lineHeight;
    canvas.width = 800;
    canvas.height = headerHeight + trackListHeight + padding * 2;
    
    // Background
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Album cover (if available)
    if (albumImage) {
      try {
        const img = new Image();
        img.crossOrigin = 'anonymous';
        await new Promise((resolve, reject) => {
          img.onload = resolve;
          img.onerror = reject;
          img.src = albumImage;
        });
        ctx.drawImage(img, padding, padding, 140, 140);
      } catch (e) {
        // Fallback if image fails to load
      }
    }
    
    // Album title and artist
    ctx.fillStyle = '#111111';
    ctx.font = 'bold 32px Arial';
    ctx.fillText(albumName, padding + 160, padding + 40);
    ctx.font = '20px Arial';
    ctx.fillStyle = '#6b7280';
    ctx.fillText(artistName, padding + 160, padding + 75);
    
    // Ranking title
    ctx.font = 'bold 24px Arial';
    ctx.fillStyle = '#111111';
    ctx.fillText('Your Final Ranking', padding, headerHeight);
    
    // Track list
    ctx.font = '18px Arial';
    tracks.forEach((track, index) => {
      const y = headerHeight + 40 + (index * lineHeight);
      const rank = index + 1;
      
      // Rank number
      ctx.fillStyle = '#111111';
      ctx.font = 'bold 18px Arial';
      ctx.fillText(`${rank}.`, padding, y);
      
      // Track name
      ctx.font = '18px Arial';
      ctx.fillText(track.name, padding + 40, y);
      
      // Duration
      const minutes = Math.floor(track.duration_ms / 60000);
      const seconds = Math.floor((track.duration_ms % 60000) / 1000);
      const durationStr = `${minutes}:${seconds.toString().padStart(2, '0')}`;
      ctx.fillStyle = '#9ca3af';
      ctx.fillText(durationStr, canvas.width - padding - 60, y);
    });
    
    // Download
    canvas.toBlob((blob) => {
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${albumName.replace(/[^a-z0-9]/gi, '_')}_ranking.png`;
      link.click();
      URL.revokeObjectURL(url);
      exportMenu.style.display = 'none';
    });
  });
}


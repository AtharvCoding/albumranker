// rank_result.js - Handle export functionality

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

// Export menu toggle
const exportBtn = document.getElementById('export-btn');
const exportMenu = document.getElementById('export-menu');
if (exportBtn && exportMenu) {
  exportBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    exportMenu.classList.toggle('show');
  });
  
  // Close menu when clicking outside
  document.addEventListener('click', (e) => {
    if (!exportMenu.contains(e.target) && e.target !== exportBtn) {
      exportMenu.classList.remove('show');
    }
  });
  
  // Prevent menu from closing when clicking inside it
  exportMenu.addEventListener('click', (e) => {
    e.stopPropagation();
  });
}

// Export CSV
const exportCsvBtn = document.getElementById('export-csv');
if (exportCsvBtn && tracks && tracks.length > 0) {
  exportCsvBtn.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();
    
    try {
      const csvRows = ['Rank,Track Name,Duration (ms),Duration (M:SS),Track Number'];
      tracks.forEach((track, index) => {
        const rank = index + 1;
        const minutes = Math.floor(track.duration_ms / 60000);
        const seconds = Math.floor((track.duration_ms % 60000) / 1000);
        const durationFormatted = `${minutes}:${seconds.toString().padStart(2, '0')}`;
        const trackName = track.name.replace(/"/g, '""'); // Escape quotes
        csvRows.push(`${rank},"${trackName}",${track.duration_ms},"${durationFormatted}",${track.track_number}`);
      });
      
      const csvContent = csvRows.join('\n');
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      const safeFileName = albumName.replace(/[^a-z0-9]/gi, '_').substring(0, 50);
      link.download = `${safeFileName}_ranking.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      exportMenu.classList.remove('show');
    } catch (error) {
      console.error('Error exporting CSV:', error);
      alert('Error exporting CSV. Please try again.');
    }
  });
}

// Export PNG/Image
const exportPngBtn = document.getElementById('export-png');
if (exportPngBtn && tracks && tracks.length > 0) {
  exportPngBtn.addEventListener('click', async (e) => {
    e.preventDefault();
    e.stopPropagation();
    
    try {
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      
      // Set canvas size
      const padding = 40;
      const lineHeight = 32;
      const headerHeight = 200;
      const trackListHeight = tracks.length * lineHeight;
      const minHeight = 400;
      canvas.width = 800;
      canvas.height = Math.max(headerHeight + trackListHeight + padding * 2, minHeight);
      
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
            img.onerror = () => {
              console.warn('Failed to load album image');
              resolve(); // Continue even if image fails
            };
            img.src = albumImage;
          });
          if (img.complete && img.naturalWidth > 0) {
            ctx.drawImage(img, padding, padding, 140, 140);
          }
        } catch (e) {
          console.warn('Error loading image:', e);
        }
      }
      
      // Album title and artist
      ctx.fillStyle = '#111111';
      ctx.font = 'bold 32px Arial';
      const titleX = albumImage ? padding + 160 : padding;
      ctx.fillText(albumName.substring(0, 40), titleX, padding + 40);
      ctx.font = '20px Arial';
      ctx.fillStyle = '#6b7280';
      ctx.fillText(artistName.substring(0, 40), titleX, padding + 75);
      
      // Ranking title
      ctx.font = 'bold 24px Arial';
      ctx.fillStyle = '#111111';
      ctx.fillText('Your Final Ranking', padding, headerHeight);
      
      // Track list
      tracks.forEach((track, index) => {
        const y = headerHeight + 50 + (index * lineHeight);
        const rank = index + 1;
        
        // Rank number
        ctx.fillStyle = '#111111';
        ctx.font = 'bold 18px Arial';
        ctx.fillText(`${rank}.`, padding, y);
        
        // Track name (truncate if too long)
        ctx.font = '18px Arial';
        ctx.fillStyle = '#111111';
        const maxTrackWidth = canvas.width - padding * 2 - 120;
        let trackName = track.name;
        const metrics = ctx.measureText(trackName);
        if (metrics.width > maxTrackWidth) {
          while (ctx.measureText(trackName + '...').width > maxTrackWidth && trackName.length > 0) {
            trackName = trackName.substring(0, trackName.length - 1);
          }
          trackName += '...';
        }
        ctx.fillText(trackName, padding + 50, y);
        
        // Duration
        const minutes = Math.floor(track.duration_ms / 60000);
        const seconds = Math.floor((track.duration_ms % 60000) / 1000);
        const durationStr = `${minutes}:${seconds.toString().padStart(2, '0')}`;
        ctx.fillStyle = '#9ca3af';
        ctx.font = '16px Arial';
        ctx.fillText(durationStr, canvas.width - padding - 60, y);
      });
      
      // Download
      canvas.toBlob((blob) => {
        if (blob) {
          const url = URL.createObjectURL(blob);
          const link = document.createElement('a');
          link.href = url;
          const safeFileName = albumName.replace(/[^a-z0-9]/gi, '_').substring(0, 50);
          link.download = `${safeFileName}_ranking.png`;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          URL.revokeObjectURL(url);
          exportMenu.style.display = 'none';
        } else {
          alert('Error generating image. Please try again.');
        }
      }, 'image/png');
    } catch (error) {
      console.error('Error exporting PNG:', error);
      alert('Error exporting image. Please try again.');
    }
  });
}


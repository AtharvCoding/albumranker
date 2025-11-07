// album_detail.js - Handle save button on album detail page

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

if (document.getElementById('save-album-btn')) {
  const saveBtn = document.getElementById('save-album-btn');
  const albumId = saveBtn.getAttribute('data-album-id');
  const isSaved = saveBtn.textContent.trim().includes('Saved');
  
  saveBtn.addEventListener('click', async () => {
    const csrfToken = getCookie('csrftoken');
    
    if (isSaved) {
      // Unsave
      try {
        const response = await fetch(`/api/unsave-album/${albumId}/`, {
          method: 'POST',
          headers: {
            'X-CSRFToken': csrfToken,
            'Content-Type': 'application/json',
          },
        });
        if (response.ok) {
          saveBtn.textContent = 'Save to My Music';
          saveBtn.style.background = '#e5e7eb';
        }
      } catch (e) {
        alert('Error unsaving album');
      }
    } else {
      // Save (metadata only)
      try {
        const response = await fetch(`/api/save-album/${albumId}/`, {
          method: 'POST',
          headers: {
            'X-CSRFToken': csrfToken,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({}),
        });
        if (response.ok) {
          const data = await response.json();
          if (data.success) {
            saveBtn.textContent = '✓ Saved';
            saveBtn.style.background = '#10b981';
          }
        }
      } catch (e) {
        alert('Error saving album');
      }
    }
  });
}


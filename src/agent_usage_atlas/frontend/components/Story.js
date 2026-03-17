function renderStory(){
  const storyKey = lang === 'en' ? 'narrative_en' : 'narrative';
  const jokesKey = lang === 'en' ? 'jokes_en' : 'jokes';
  const narrative = data.story[storyKey] || data.story.narrative || [];
  const jokes = data.story[jokesKey] || data.story.jokes || [];
  const blocks = [
    ...narrative,
    ...jokes.map(txt => ({icon: 'fa-comment-dots', text: txt}))
  ];
  document.getElementById('story-list').innerHTML = blocks.map(block => `
    <div class="si"><i class="fa-solid ${block.icon}"></i><div>${block.text}</div></div>
  `).join('');
}

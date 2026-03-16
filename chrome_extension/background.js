chrome.downloads.onChanged.addListener((delta) => {
  if (delta.state && delta.state.current === 'complete') {
    chrome.downloads.search({ id: delta.id }, (results) => {
      if (results && results.length > 0) {
        let file = results[0];
        let filename = file.filename;

        // Verifica se é pdf, epub, mobi
        let ext = filename.split('.').pop().toLowerCase();
        if (['pdf', 'epub', 'mobi'].includes(ext)) {
          console.log("Download de livro detectado, enviando para ISBN Renamer: ", filename);
          
          chrome.runtime.sendNativeMessage(
            'com.kassio.isbn_renamer',
            { action: "process_file", path: filename },
            (response) => {
              if (chrome.runtime.lastError) {
                console.error("Erro no Native Messaging (Host nao encontrado ou não configurado corretamente):", chrome.runtime.lastError.message);
              } else {
                console.log("Resposta do Host:", response);
              }
            }
          );
        }
      }
    });
  }
});

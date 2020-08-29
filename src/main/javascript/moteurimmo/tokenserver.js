var http = require('http')
var hash = require('object-hash')
let crypto = require('crypto');

http.createServer(function (request, response) {
    let body = [];
    request.on('data', (chunk) => {
        body.push(chunk);
    }).on('end', () => {
        try {
            body = JSON.parse(Buffer.concat(body).toString());
            response.statusCode = 200;
            response.end(
                crypto.createHmac("sha256", "immo").update(hash(body, {excludeKeys: e => "token" === e})).digest("hex")
            )
        } catch (e) {
            response.statusCode = 500;
            response.setHeader('content-type', 'application/json');
            response.end(JSON.stringify(e, Object.getOwnPropertyNames(e)));
        }

    });
}).listen(18081)

console.log('Server running at http://127.0.0.1:18081/')

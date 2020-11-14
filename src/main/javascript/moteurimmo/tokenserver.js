const hash = require('object-hash')
const crypto = require('crypto');
const express = require('express')
const bodyParser = require('body-parser')


const app = express()
app.use(bodyParser.json());
const port = 18081

app.post('/token', (req, res) => {
    let body = req.body;
    res.status(200)
    res.send(crypto.createHmac("sha256", "immo").update(hash(body, {excludeKeys: e => "token" === e})).digest("hex"))
});

app.post('/decrypt', (req, res) => {
    const key = req.body.key || "03438EB3989626ACB2C723A8D7BCF276";
    const e = req.body.req;
    let a = crypto.createDecipheriv("aes-256-cbc", Buffer.from(key), Buffer.from(e.iv, "hex"))
        , r = a.update(Buffer.from(e.encryptedData, "hex"));
    res.status(200)
    res.send(Buffer.concat([r, a.final()]).toString());
});

app.listen(port, () => {
    console.log(`Server running at port: ${port}`)
});

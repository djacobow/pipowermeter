var sqlite3 = require('sqlite3').verbose();

var CredDB = function(dbfname) {
    var tthis = this;
    this.fname = dbfname;
    this.db = new sqlite3.Database(dbfname, sqlite3.OPEN_CREATE | sqlite3.OPEN_READWRITE);
    this.setup();
};

CredDB.prototype.close = function() {
    if (this.db) this.db.close();
};

CredDB.prototype.setup = function() {
    var sql0 = [ 
        'CREATE TABLE IF NOT EXISTS credentials(',
        'rowid INTEGER PRIMARY KEY,',
        'name VARCHAR(255) UNIQUE,',
        'serial VARCHAR(255),',
        'jsblob TEXT)',
    ].join('');
    var sql1 = 'CREATE INDEX IF NOT EXISTS serial_idx ON credentials(serial);';

    var tthis = this;
    this.db.serialize(function() {
        var err = tthis.db.run(sql0);
        err = tthis.db.run(sql1);
    });

};

CredDB.prototype.add = function(data,cb) {
    // console.log('CredDB.add()',data);
    var sql = 'INSERT OR REPLACE INTO credentials (name,serial,jsblob) VALUES(?,?,?)';
    this.db.run(sql,[data.node_name,data.serial_number,JSON.stringify(data)],function(aerr,ares) {
        if (aerr) console.log('adderr',aerr);
        // if (ares) console.log('addres',ares);
        cb(ares);
    });
};

CredDB.prototype.getBySerial = function(serial, cb) {
    var sql = 'SELECT jsblob FROM credentials WHERE serial = ?';
    this.db.all(sql,[serial],function(gerr,rows) {
        if (gerr || (rows.length !=  1)) return cb(null);
        return cb(JSON.parse(rows[0].jsblob));
    });
};

CredDB.prototype.get = function(name,cb) {
    var sql = 'SELECT jsblob FROM credentials WHERE name = ?';
    this.db.all(sql,[name],function(gerr,rows) {
        if (gerr || (rows.length !=  1)) return cb(null);
        return cb(JSON.parse(rows[0].jsblob));
    });
};

CredDB.prototype.getAll = function(cb) {
    var sql = 'SELECT name FROM credentials';
    this.db.all(sql,[],function(gerr,rows) {
        if (gerr || !rows.length) return cb([]);
        names = rows.map(function(r) { return r.name; });
        return cb(names);
    });
};

module.exports = CredDB;


/*jshint esversion:6 */
var fs = require('fs');
var crypto = require('crypto');
var CredDB = require('./CredDB');

// I could not get the node 9.3.0 crypto sha512 module
// to work correctly, so I am using this one instead. I think
// it was an encoding issue on my end, but I gave up trying
// to resolve it, and the one below works
var sha512 = require('js-sha512').sha512;

const DEBUG_AUTH = false;
const MAX_PROV_ATTEMPTS = 5;

var Dbg = function(n,b) {
    if (DEBUG_AUTH) {
        console.log('DBG ' + n + '\t:\t' + b.toString('base64'));
    }
};


var Provisioner = function(provisioned_fn, provtoks_fn) {
    this.provtoks_fn = provtoks_fn;
    this.provisioned_fn = provisioned_fn;
    this.provtoks = [];
    this.cdb = new CredDB(this.provisioned_fn);
};

Provisioner.prototype.makeRandString = function(l) {
  var possible = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  var text = crypto.randomBytes(l).toString('base64');
  return text;
};

var loadFJS = function(fn) {
    try {
        var fstring = fs.readFileSync(fn);
        var fdata = JSON.parse(fstring);
        return fdata;
    } catch (ex) {
        console.log('Error loading file: ' + fn);
        console.log(ex);
    }
    return null;
};

Provisioner.prototype.tokValid = function(b,cb) {
    if (!b.hasOwnProperty('identification')) return cb(false);

    var id = b.identification;

    if (!(id.hasOwnProperty('node_name') &&
          id.hasOwnProperty('salt') &&
          id.hasOwnProperty('salted_tok'))) return cb(false);

    var node_name = id.node_name;

    this.cdb.get(node_name, function(pi) {

        if (!pi) return cb(false);

        if  (!(pi.hasOwnProperty('tok_hash') &&
               pi.hasOwnProperty('serial_number') &&
               pi.hasOwnProperty('salt'))) return cb(false);

        var tok_hash = Buffer.from(pi.tok_hash, 'base64');
        var id_salt  = Buffer.from(id.salt, 'base64');
        var combined = Buffer.concat([tok_hash, id_salt]);

        Dbg('tok_hash', tok_hash);
        Dbg('id_salt',  id_salt);
        Dbg('combined', combined);

        var h1_lcl = Buffer.from(sha512.create().update(combined).digest());
        var h1_rem = Buffer.from(id.salted_tok, 'base64');

        Dbg('h1_lcl', h1_lcl);
        Dbg('h1_rem', h1_rem);

        return cb(!Buffer.compare(h1_lcl,h1_rem));
    });

};

Provisioner.prototype.loadProvToks = function() {
    var d  = loadFJS(this.provtoks_fn);
    if (d) {
        this.provtoks = d;
    }
    return this.provtoks;
};

Provisioner.prototype.load = function() {
    this.loadProvToks();
};

Provisioner.prototype.getProvisioned = function(cb) {
    return this.cdb.getAll(cb);
};

Provisioner.prototype.provTokValid = function(candidate) {
    for (var i=0; i<this.provtoks.length; i++) {
        if (candidate == this.provtoks[i]) return true;
    }
    return false;
};


Provisioner.prototype.createNew = function(name, serial, nows) {
    var new_token = crypto.randomBytes(64);
    var new_salt  = crypto.randomBytes(64);
    var sbuffer   = Buffer.from(serial);
    var combined  = Buffer.concat([new_token, new_salt, sbuffer]);
    var new_hash = Buffer.from(sha512.create().update(combined).digest());

    Dbg('new_token',new_token);
    Dbg('new_salt',new_salt);
    Dbg('sbuffer',sbuffer);
    Dbg('combined',combined);
    Dbg('new_hash',new_hash);

    var new_salt_str = new_salt.toString('base64');

    var rv = {
        new_entry: {
            serial_number: serial,
            node_name: name,
            provisioning_attempts: 1,
            prov_date: nows,
            salt: new_salt_str,
            tok_hash: new_hash.toString('base64'),
        },
        return_data: {
            serial_number: serial,
            node_name: name,
            provisioning_attempts: 1,
            prov_date: nows,
            server_salt: new_salt_str,
            token: new_token.toString('base64'),
        },
    };
    return rv;
};

Provisioner.prototype.provision = function(req, cb) {
    var serial  = req.serial_number || '';
    var provtok = req.provtok || '';
    var name    = req.name || '';

    var nows = (new Date()).toISOString();
    var d = null;
    var tthis = this;
    if (this.provTokValid(provtok)) {
        tthis.cdb.get(name,function(existing) {
            if (existing) {
                if ((existing.provisioning_attempts < MAX_PROV_ATTEMPTS) &&
                    (serial == existing.serial_number)) {
                    existing.provisioning_attempts += 1;
                    existing.prov_date = nows;
                    tthis.cdb.add(existing,function() {
                        return cb(existing);
                    });
                } else {
                    return cb(null);
                }

            } else {
                tthis.cdb.getBySerial(serial, function(existing) {
                    if (existing) {
                        var provisioning_attempts = existing.provisioning_attempts;
                        if (provisioning_attempts < MAX_PROV_ATTEMPTS) {
                            d = tthis.createNew(existing.node_name, serial, nows);
                            provisioning_attempts += 1;
                            d.new_entry.provisioning_attempts = provisioning_attempts;
                            d.return_data.provisioning_attempts = provisioning_attempts;
                            tthis.cdb.add(d.new_entry,function() {
                                return cb(d.return_data);
                            });
                        } else {
                            return cb(null);
                        }
                    } else {
                        d = tthis.createNew(name, serial, nows);
                        tthis.cdb.add(d.new_entry,function() {
                            return cb(d.return_data);
                        });
                    }
                });
            }
        });
    } else {
        return cb(null);
    }
};

module.exports = Provisioner;

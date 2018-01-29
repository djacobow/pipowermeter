/* jshint esversion: 6 */
var Provisioner   = require('./Provisioner');
var Mailbox       = require('./Mailbox');
var fs            = require('fs');
var express       = require('express');

function copyWithoutKey(ind, banned) {
    var od = {};
    var keys = Object.keys(ind);
    for (var i=0; i<keys.length; i++) {
        var key = keys[i];
        if (key != banned) od[key] = ind[key];
    }
    return od;
}


var DataAcceptor = function(dev_config) {
    this.config = dev_config;
    this.pv = new Provisioner(this.config.provisioned_clients_path,
                              this.config.provisioning_tokens_path);
    this.pv.load();
    this.mb = new Mailbox(dev_config.mailbox, this.pv, this.fireHook.bind(this));
    this.setupDefaults(); // FIXME: use the callback
    this.loadSensorParams();
    this.hooks = {};

};

DataAcceptor.prototype.setupRoutes = function(router) {
    router.post('/push',          this.handleDataPost.bind(this));
    router.post('/ping',          this.handlePing.bind(this));
    router.head('/time',          this.handleTimeHead.bind(this));
    router.get('/params',         this.handleParamsGet.bind(this));
    router.post('/setup/:name',   this.handleProvision.bind(this));
    var mbrouter = express.Router();
    router.use('/mbox', mbrouter);
    this.mb.setupRoutes(mbrouter);
};

DataAcceptor.prototype.setHook = function(name,func) {
    if (name && name.length && (typeof func === 'function')) {
        if (this.hooks.hasOwnProperty(name)) {
            this.hooks[name].push(func);
        } else {
            this.hooks[name] = [ func ];
        }
    } else {
        console.warn('hook not set for ' + name);
    }
};

DataAcceptor.prototype.fireHook = function(name, data) {
    // maybe fire these async?
    var hooks = this.hooks;
    if (hooks.hasOwnProperty(name)) {
        for (var i=0; i<hooks[name].length; i++) {
            try {
                var hkfn = hooks[name][i];
                hkfn(name, data);
            } catch (e) {
                console.log(e);
           }
        }
    }
};

DataAcceptor.prototype.handleTimeHead = function(req, res) {
    res.writeHead(200, { 'server_time_epoch_ms': Date.now(), });
    res.end();
};

DataAcceptor.prototype.handleProvision = function(req, res) {
    var arg = {
        name: req.params.name.replace('/',''),
        serial_number: req.body.serial_number || '',
        provtok: req.body.provtok || '',
    };
    var tthis = this;
    this.pv.provision(arg,function(rv) {
        if (rv) {
            tthis.getdevicestate(rv.node_name, true);
            res.status('200');
            var sv = copyWithoutKey(rv, 'serial_number');
            res.json(sv);
            tthis.fireHook('provision',rv.node_name);
            return;
        }
        res.status('403');
        res.json({message: 'begone!'});
    });
};


DataAcceptor.prototype.loadSensorParams= function() {
    this.cparams = JSON.parse(fs.readFileSync(this.config.device_params_path, 'utf8'));
};


DataAcceptor.prototype.getdevicelist= function() {
    return Object.keys(this.cstates);
};

DataAcceptor.prototype.getdevicestate = function(name, startup = false) {
    var cs = this.cstates[name] || null;
    if (startup && !cs) {
        cs = {
            node_name: name,
            busy: false,
            valid: false,
        };
        this.cstates[name] = cs;
    }
    return cs;
};

DataAcceptor.prototype.setupDefaults = function(cb) {
    console.log('setupDefaults()');
    var cstates = {};
    this.cstates = cstates;
    var othis = this;
    this.pv.getProvisioned(function(names) {
        console.log('back from GetProvisioned');
        names.forEach(function(node_name) {
            console.log('node_name',node_name);
            othis.getdevicestate(node_name, true);
        });
        if (cb) cb(null);
        return;
    });
};

var safeJSONParse = function(s) {
    try {
        return JSON.parse(s);
    } catch(e) {
        console.log('Parse exception',e);
    }
    return {};
};


DataAcceptor.prototype.handleParamsGet = function(req, res) {
    var b = safeJSONParse(req.query.qstr);
    var tthis = this;
    this.pv.tokValid(b,function(v) {
        if (v) {
            res.status(200);
            if (tthis.cparams.hasOwnProperty(b.identification.node_name)) {
                res.json(this.cparams[b.identification.node_name]);
            } else {
                res.json({});
            }
            tthis.fireHook('getparams',b.identification.node_name);
            return;
        }
        res.status(403);
        res.json({ message: 'nyet.' });
    });
};


DataAcceptor.prototype.handlePing = function(req, res) {
    var iaobj = this;
    var b = req.body;
    var rv = { message: 'nope.', };
    var rvs = 403;

    var tthis = this;
    this.pv.tokValid(b,function(v) {
        if (v) {
            try {
                var node_name= b.identification.node_name;
                var cstate = tthis.getdevicestate(node_name);
                if (true) {
                    var public_ip = req.headers['x-forwarded-for'];
                    if (!b.hasOwnProperty('diagnostic')) b.diagnostic = {};
                    if (!b.diagnostic.hasOwnProperty('host')) b.diagnostic.host = {};
                    b.diagnostic.host.public_ip = public_ip;
                }
                cstate.ping = {
                    'date': b.date,
                    'diagnostic': b.diagnostic,
                    'source_type': b.source_type,
                };
                rvs = 200;
                rv = {message: 'thanks!'};
                tthis.fireHook('ping',node_name);
            } catch (e) {
                rvs = 400;
                rv = {message: 'malformed submission'};
                console.log(e);
            }
        }
        res.status(rvs);
        res.json(rv);
    });
};


DataAcceptor.prototype.handleDataPost = function(req, res) {
    // console.log('handleDataPost()');
    var iaobj = this;
    var b = req.body;
    var rv = { message: 'nope.', };
    var rvs = 403;
    // console.log(JSON.stringify(b,null,2));
    var tthis = this;
    this.pv.tokValid(b,function(v) {
        if (v) {
            var node_name= b.identification.node_name;
            var cstate = tthis.getdevicestate(node_name);
            if (!cstate) {
                console.log('unknown device: ' + node_name);
                res.status('403');
                res.json({message:'unknown device'});
                return;
            }
            try {
                cstate.busy = true;
                cstate.valid  = false;
                if (true) {
                    var public_ip = req.headers['x-forwarded-for'];
                    if (!b.hasOwnProperty('diagnostic')) b.diagnostic = {};
                    if (!b.diagnostic.hasOwnProperty('host')) b.diagnostic.host = {};
                    b.diagnostic.host.public_ip = public_ip;
                }
                cstate.diagnostic = b.diagnostic;
                cstate.source_type = b.source_type;
                cstate.date = b.date;
                cstate.sensor_data = b.sensor_data;
                cstate.upload_number += 1;
                cstate.valid = true;
                cstate.busy = false;
                rv = {message: 'thanks!', upload_number: cstate.upload_number};
                rvs = 200;
                tthis.fireHook('push',node_name);
            } catch(e) {
                console.log(e);
                cstate.valid = false;
                cstate.busy = false;
                rv = {message: 'malformed submission' };
                rvs = 400;
            }
       }
       res.status(rvs);
       res.json(rv);
    });
};



module.exports = DataAcceptor;


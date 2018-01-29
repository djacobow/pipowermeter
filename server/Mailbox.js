/*jshint esversion:6 */
var uuid          = require('uuid/v4');

var Mailbox = function(cfg, provisioner, fireHook) {
    this.config = cfg;
    this.pv = provisioner;
    this.mq = {
        outbox: {},
        inbox:  {},
    };
    this.fireHook = fireHook;

    this.message_types = { 'shell_script': 1 };

};

Mailbox.prototype.setupRoutes = function(router) {
    this.router = router;
    router.post('/respond',  this.handleRespond.bind(this));
    router.get('/fetch',     this.handleFetch.bind(this));
};

Mailbox.prototype.getResponses = function() {
    var queued_responses = this.mq.inbox;
    this.mq.inbox = {};
    return queued_responses;
};


Mailbox.prototype.queueNew = function(node_name, type = 'shell_script', payload = '') {
    if (this.message_types.hasOwnProperty(type)) {
        var msg_id = 'msg/' + uuid();
        var b = {
            msg_id: msg_id,
            type: type,
            payload: payload,
        };
        if (!this.mq.outbox.hasOwnProperty(node_name)) {
            this.mq.outbox[node_name] = [];
        }
        this.mq.outbox[node_name].push(b);
        return msg_id;
    }
    return null;
};

var safeJSONParse = function(s) {
    try {
        return JSON.parse(s);
    } catch(e) { 
        console.log('Parse exception',e);
    }
    return {};
};

Mailbox.prototype.handleFetch = function(req, res) {
    var b = safeJSONParse(req.query.qstr);    
    var tthis = this;
    this.pv.tokValid(b,function(v) {
        if (v) {
            res.status(200);
            var node_name = b.identification.node_name;
            var avail_messages = tthis.mq.outbox[node_name];
            if (avail_messages && 
                Array.isArray(avail_messages) &&
                avail_messages.length) {
                var max_messages = tthis.config.max_per_get;
                var ret_messages = [];
                while (max_messages && avail_messages.length) {
                    ret_messages.push(avail_messages.shift());
                    max_messages -= 1;
                }
                res.json(ret_messages);

            } else {
                res.json([]);
            }
            tthis.fireHook('fetchmail',node_name);
            return;
        }
        res.status(403);
        res.json({ message: 'survey says: Buzz!' });
    });
};

Mailbox.prototype.handleRespond = function(req, res) {
    var b = req.body;

    var rv = { message: 'nope.', };
    var rvs = 403;

    var tthis = this;
    this.pv.tokValid(b,function(v) {
        if (v) {
            var node_name = b.identification.node_name;
            var responses = b.responses;
            if (responses && Array.isArray(responses) && responses.length) {
                var kosher_responses = [];
                while (responses.length) {
                    var response = responses.shift();
                    if (response.hasOwnProperty('msg_id') &&
                        response.msg_id.length &&
                        response.hasOwnProperty('type') &&
                        (response.type == 'response') &&
                        response.hasOwnProperty('payload')) {
                        kosher_responses.push(response);
                    }
                }
                if (kosher_responses.length) {
                    if (!tthis.mq.inbox.hasOwnProperty(node_name)) {
                        tthis.mq.inbox[node_name] = [];
                    }
                    while (kosher_responses.length) {
                        var kosher_response = kosher_responses.shift();
                        tthis.mq.inbox[node_name].push(kosher_response);
                        if (!rv.accepted) rv.accepted = [];
                        rv.accepted.push(kosher_response.msg_id);
                    }
                    rv.messsage = 'ok';
                    tthis.fireHook('respondmail',node_name);
                } else {
                    rvs = 406;
                    rv.message = 'No responses provided were acceptable.';
                }
            } else {
                rvs = 406;
                rv.message = 'No responses to post';
            }
        }
        res.status(rvs);
        res.json(rv);
    });
};

module.exports = Mailbox;


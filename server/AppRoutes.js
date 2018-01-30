/*jshint esversion:6 */

const MAX_MEMORY_STORAGE_TIME = 1 * 60 * 60; // seconds

var AppRoutes = function(app_config, dataacceptor) {
    this.config = app_config;
    this.da = dataacceptor;
    this.db = {};
};

AppRoutes.prototype.setupRoutes = function(router) {
    router.get('/sensornames',               this.handleListGet.bind(this));
    router.get('/status/:name',              this.handleStatusGet.bind(this));
    router.get('/tsdata/:devname/:varname',  this.handleTSGet.bind(this));
};

AppRoutes.prototype.handleListGet = function(req, res) {
    console.log('GET list of sensors');
    var devlist = this.da.getdevicelist();
    res.json(devlist);
};

AppRoutes.prototype.handleStatusGet = function(req, res) {
    var name = req.params.name;
    var cstate = this.da.getdevicestate(name) || null;
    rv = {};
    console.log('handleStatusGet: ' + name);
    if (cstate) {
        Object.keys(cstate).forEach(function(k) {
            if (k !== 'image_jpeg') rv[k] = cstate[k];
        });
    } else {
        rv.message = 'no such sensor';
    }
    res.json(rv);
};

AppRoutes.prototype.removeOldData = function() {
    var now = Math.round(((new Date()).getTime()) * 1000 + 0.5);
    Object.keys(cstate.sensor_data).forEach(function(k) {
        Object.keys(cstate.sensor_data[k]).foreach(function(ts) {
            var age = now - ts;
            if (age > MAX_MEMORY_STORAGE_TIME) {
                delete cstate.sensor_data[k][ts];
            }
        });
    });
};

AppRoutes.prototype.pushHook = function(hookname, devname) {
    console.log('AppRoutes::pushHook ' + hookname + ' ' + devname);
    if (hookname == 'push') {
        if (!(devname in this.db)) this.db[devname] = {};
        var cstate = this.da.getdevicestate(devname) || null;
        if (cstate && cstate.sensor_data) {
            // console.log(this.db);
            var arthis = this;
            Object.keys(cstate.sensor_data).forEach(function(ts) {
                arthis.db[devname][ts] = cstate.sensor_data[ts];
            });
            // console.log(JSON.stringify(cstate,null,2));
        }
    }
};

AppRoutes.prototype.handleTSGet = function(req, res) {
    var devname = req.params.devname;
    var varname = req.params.varname;
    var dbdata = this.db[devname];
    rv = {};
    if (dbdata) {
        console.log('handleTSGet()');
        var timestamps = Object.keys(dbdata);
        rv.timestamps = timestamps;
        rv[varname] = timestamps.map(function(ts) { 
            if (varname in dbdata[ts]) {
                return dbdata[ts][varname].value;
            } else {
                return null;
            }
        });
    }
    res.json(rv);
};

module.exports = AppRoutes;


/*jshint esversion:6 */

const MAX_MEMORY_STORAGE_TIME = 1 * 60 * 60; // seconds
const CLEANING_INTERVAL = 5 * 60 * 1000; // milllisecond

var AppRoutes = function(app_config, dataacceptor) {
    this.config = app_config;
    this.da = dataacceptor;
    this.db = {};
    this.run_cleaner = true;
};

AppRoutes.prototype.setupRoutes = function(router) {
    router.get('/sensornames',               this.handleListGet.bind(this));
    router.get('/status/:name',              this.handleStatusGet.bind(this));
    router.get('/tsdata/:devname/:varname',  this.handleTSGet.bind(this));
    this.cleaner();
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

AppRoutes.prototype.cleaner = function() {
    if (this.run_cleaner) {
        this.removeOldData();
        setTimeout(this.cleaner.bind(this), CLEANING_INTERVAL);
    }
};

AppRoutes.prototype.removeOldData = function() {
    var now = Math.round(((new Date()).getTime()) / 1000 + 0.5);
    var tthis = this;
    var devices = this.da.getdevicelist();
    devices.forEach(function(k) {
        var cstate = tthis.da.getdevicestate(k);
        if (cstate && cstate.sensor_data) {
            var timestamps = Object.keys(cstate.sensor_data);
            // console.log(timestamps);
            timestamps.forEach(function(ts) {
                tsint = parseInt(ts);
                // console.log('now: ' + now.toString() + ' ts: ' + tsint.toString());
                var age = now - tsint;
                if (age > MAX_MEMORY_STORAGE_TIME) {
                    delete cstate.sensor_data[ts];
                }
            });
        }
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


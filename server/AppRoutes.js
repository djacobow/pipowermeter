
var AppRoutes = function(app_config, dataacceptor) {
    this.config = app_config;
    this.da = dataacceptor;
};

AppRoutes.prototype.setupRoutes = function(router) {
    router.get('/sensornames',   this.handleListGet.bind(this));
    router.get('/status/:name',  this.handleStatusGet.bind(this));
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
//    if (cstate) {
//        Object.keys(cstate).forEach(function(k) {
//            if (k !== 'image_jpeg') rv[k] = cstate[k];
//        });
//    } else {
//        rv.message = 'no such sensor';
//    }
//    res.json(rv);
};


module.exports = AppRoutes;


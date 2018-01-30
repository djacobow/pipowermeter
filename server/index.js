
var express       = require('express');
var bodyParser    = require('body-parser');
var fs            = require('fs');
var DataAcceptor  = require('./DataAcceptor');
var AppRoutes     = require('./AppRoutes');
var file_helpers  = require('./static_helpers');

var app           = express();
var port = process.env.TURKEY_PORT || 9090;

var setup_debug_hooks = function(da) {

    var w = function(hname,sname) {
        console.log('Device action: [' + hname + '] ' + sname);
    };
    debug_hooknames = ['provision','push','ping','getparams','fetchmail'];
    for (var i=0; i<debug_hooknames.length; i++) {
        da.setHook(debug_hooknames[i], w);
    }
    da.setHook('respondmail', function(hname, sname) {
        w(hname, sname);
        r = da.mb.getResponses();
        console.log('responses',JSON.stringify(r,null,2));
    });
};

if (require.main === module) {

    var dev_config = {
        'provisioned_clients_path': './provisioned.sqlite',
        'provisioning_tokens_path': './provisioning_tokens.json',
        'device_params_path': './sensor_params.json',
        'mailbox': {
            'max_per_get': 5,
        },
    };
    var app_config = {
        // for future
    };

    var da = new DataAcceptor(dev_config);
    var ar = new AppRoutes(app_config, da);
    setup_debug_hooks(da);
    da.setHook('push', ar.pushHook.bind(ar));

    var toprouter = express.Router();
    var devrouter = express.Router();
    var approuter = express.Router();

    da.setupRoutes(devrouter);
    ar.setupRoutes(approuter);

    da.mb.queueNew('d3s_f9Ke0q5tFc','shell_script','echo Hello, World!');

    toprouter.get('/',              file_helpers.handleRoot);
    toprouter.get('/static/:name',  file_helpers.handleStaticFile);
    
    app.use(bodyParser.urlencoded({extended: true, limit: '50mb'}));
    app.use(bodyParser.json({limit:'50mb'}));

    app.use('/pwrmon/device', devrouter);
    app.use('/pwrmon/app', approuter);
    app.use('/pwrmon', toprouter);

    app.listen(port);
    console.log('PowerMon running on port ' + port);
}



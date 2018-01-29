/* jshint esversion:6 */
console.log('start');
var senselems = {};
var current_results = {};

var makeChartFromArray = function(type, target, data, options = null) {
    console.log('makeChartFromArry()');
    var drawChart = function() {
        console.log('drawChart()');
        var cdata = google.visualization.arrayToDataTable(data);
        var chart = null;
        switch (type) {
            case 'bar': 
                chart = new google.visualization.ColumnChart(target); 
                break;
            case 'pie': 
                chart = new google.visualization.PieChart(target); 
                break;
            case 'line': 
                chart = new google.visualization.LineChart(target); 
                break;
            default:
                chart = new google.visualization.ColumnChart(target); 
        }

        chart.draw(cdata, options);
    };
    drawChart();
};


var getDataElementFromDottedName = function(data,name) {
    var d = data;
    var names = name.split(/\./);
    try {
        while (names.length) {
            n = names.shift();
            d = d[n];
        }
    } catch(e) {
        dataval = '_missing';
    }

    if (typeof d === 'object') {
        d = JSON.stringify(d);
    }

    return d;
};


var makeUL = function(target, data, names) {
    removeChildren(target);
    var ul = document.createElement('ul');
    target.appendChild(ul);
    var pns = Object.keys(names);
    for (var i=0;i<pns.length;i++) {
        var friendly_name = pns[i];
        var data_name = names[friendly_name].n;
        var unit = names[friendly_name].u;

        var dataval = getDataElementFromDottedName(data,data_name);

        try {
            var li = document.createElement('li');
            li.innerText = friendly_name + ': ' + dataval + ' ' + unit;
            ul.appendChild(li);
        } catch (e) {
        }
    }
    return ul;
};

var makeLeft = function(name, d) {
    // console.log(d.sensor_data);
    var tdl = senselems[name].tdl;    
    removeChildren(tdl);

    var title = document.createElement('a');
    title.innerText = name;
    title.href = 'app/status/' + name;
    tdl.appendChild(title);
     
    var cdiv = document.createElement('div');
    tdl.appendChild(cdiv);
    var carry = [];
    carry.push(['bin','count']);
    for (var j=0;j<d.sensor_data.spectrum.length;j++) {
        carry.push([j,d.sensor_data.spectrum[j]]);
    }

    makeChartFromArray('line',
                       cdiv,
                       carry,
                       {'title':name});
};

var tablenames = {
    sensor_fields: {
        'Neutron Count': { n: 'neutron_count', u: '' },
        'Integration Time': { n: 'time', u: 'ms' },
        'Temperature': { n: 'temperature', u: '\u2103' },
        'Device Serial': { n: 'serial', u: '' },
        'Gain': {n : 'gain', u: '' },
        'Bias': {n : 'bias', u: '' },
        'LLD (gamma)': { n: 'lld-g', u: '' },
        'LLD (neutron)': { n: 'lld-n', u: '' },
        'Battery Level': { n: 'batteryLevel', u: '%' },
        'Charge Rate': { n: 'batteryChargeRate', u: '' },
        'Battery Temp': { n: 'batteryTemperature', u: '\u2103' },
    },
    message_fields: {
        'Date': { n: 'date', u: '' },
        'Node Name': { n: 'node_name', u: '' },
        // 'host.ip': { n: 'diagnostic.host.ip', u: '' },
        'host.public_ip': { n: 'diagnostic.host.public_ip', u: '' },
        'host.name': { n: 'diagnostic.host.name', u: '' },
        'host.uptime': { n: 'diagnostic.host.uptime', u: '' },
        'service.uptime': { n: 'diagnostic.service.uptime', u: '' },
        'Type': { n: 'source_type', u: '' },
    },
};

var makeCenter = function(name, d) {
    var tdc = senselems[name].tdc;    
    makeUL(tdc, d.sensor_data, tablenames.sensor_fields);
};

var addLocalIPs = function(d) {
    var li = document.createElement('li');
    var ips = {};
    if (d && d.diagnostic && d.diagnostic.host && d.diagnostic.host.ifaces) {
        var ifnames = Object.keys(d.diagnostic.host.ifaces);
        for (var i=0; i<ifnames.length; i++) {
            var ifn = ifnames[i];
            if (ifn != 'lo') {
                var ifd = d.diagnostic.host.ifaces[ifn];
                if (ifd) {
                    var inet = ifd[2];
                    if (inet) {
                        var first_inet = inet[0];
                        if (first_inet) {
                            var addr = first_inet.addr;
                            if (addr) ips[ifn] = addr;
                        }
                    }
                }
            }
        }
    }
    li.innerText = 'host.ifaces: ' + JSON.stringify(ips);
    return li;
};

var makeRight = function(name, d) {
    var tdr = senselems[name].tdr;    
    var ul = makeUL(tdr, d, tablenames.message_fields);
    ul.appendChild(addLocalIPs(d));
    
    var el = document.createElement('p');
    now = new Date();
    var latest = new Date(0);
    if (d.date) latest = new Date(d.date);
    if (d.ping && d.ping.date) {
        var x = new Date(d.ping.date);
        if (x > latest) latest = x;
    }

    if ((now - latest) > (5 * 60 * 1000)) {
        el.innerText = 'Device is DOWN';
        el.style.color = 'red';
    } else {
        el.innerText = 'Device is UP';
        el.style.color = 'green';
    }
    tdr.appendChild(el);
};


var getSensorList = function(cb) {
    console.log('getSensorList()');
    getJSON('/radmon/app/sensornames', function(err, data) {
        if (err) {
            console.log('Error getting sensor list: ' + err);
            return cb(err);
        } else {
            return cb(null,data);
        }
    });
};

var checkData = function(name, cb) {
    console.log('checkData()');
    getJSON('/radmon/app/status/' + name, function(err, new_data) {
        var old_data = current_results[name];
    
        if (err) {
            console.log('checkData err: ' + err);
            return cb('err');
        } else if (!new_data || !old_data) {
            console.log('checkData err, missing sensor');
            return cb('err missing sensor');
        } else if (new_data) {
            console.log('checkData ok');
            var old_image_date = new Date(old_data.date || 0);
            var new_image_date = new Date(new_data.date);
            var old_ping_date  = old_image_date;
            if (old_data.hasOwnProperty('ping')) {
                old_ping_date = new Date(old_data.ping.date);
            }
            var new_ping_date  = old_ping_date;
            if (new_data.hasOwnProperty('ping')) {
                new_ping_date = new Date(new_data.ping.date);
            }
            var refresh   = !old_data || 
                            (new_image_date > old_image_date);
            var new_ping  = (new_ping_date > old_ping_date);

            if (false) {
                console.log('old_image_date: ' + old_image_date);
                console.log('new_image_date: ' + old_image_date);
                console.log('old_ping_date: ' + old_ping_date);
                console.log('new_ping_date: ' + old_ping_date);
                console.log('refresh: ' + refresh);
                console.log('new_ping: ' + new_ping);
            } 

            if (refresh) {
                makeLeft(name, new_data);
                makeCenter(name, new_data);
                makeRight(name, new_data);
            }
            current_results[name] = new_data;
            return cb(null,new_data);
        } else {
            return cb('skip');
        }
    });
};


var makeDeviceLayout = function(senslist,cb) {
    console.log('makeDeviceLayout()');
    var topdiv = document.getElementById('topdiv');
    var toptable = document.createElement('table');
    toptable.style.width = "100%";
    topdiv.appendChild(toptable);
    for (var i=0;i < senslist.length; i++) {
        var cname = senslist[i];
        var ntr = document.createElement('tr');
        toptable.appendChild(ntr);
        tdl = document.createElement('td');
        tdc = document.createElement('td');
        tdr = document.createElement('td');
        tdl.style.width = "50%";
        tdc.style.width = "25%";
        tdr.style.width = "25%";
        ntr.appendChild(tdl);
        ntr.appendChild(tdc);
        ntr.appendChild(tdr);
        senselems[cname] = {
            tr: ntr,
            tdl: tdl,
            tdc: tdc,
            tdr: tdr,
        };
        current_results[cname] = {
            valid: false,
            busy: false,
            date: '',
        };
    }
    return cb();
};

var startTimer = function() {
    var senslist = Object.keys(senselems);
    async.each(senslist, function(sensn,cb) {
        console.log('async.each: ' + sensn);
        checkData(sensn, function(cerr, cd) {
            cb();
        });
    },
    function (err) {
        window.setTimeout(startTimer, 5000);
    });
};

var init = function() {
    google.charts.load('current', {'packages':['corechart','bar']});

    google.charts.setOnLoadCallback(function() {
        console.log('google charts loaded');
        getSensorList(function(err,insensors) {
            console.log(insensors);
            if (!err) {
                makeDeviceLayout(insensors, function() {
                    startTimer();
                });
            }
        });
    });
};



init();



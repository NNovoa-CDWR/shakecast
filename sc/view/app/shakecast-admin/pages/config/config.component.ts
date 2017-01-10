import { Component,
         OnInit,
         OnDestroy } from '@angular/core';

import { ConfigService } from './config.service'
import { TimeService } from './time.service'

@Component({
  selector: 'config',
  templateUrl: 'app/shakecast-admin/pages/config/config.component.html',
  styleUrls: ['app/shakecast-admin/pages/config/config.component.css']
})
export class ConfigComponent implements OnInit, OnDestroy {
    private subscriptions: any[] = [];
    public configs: any = {"Logging": {"log_file": "", "log_level": "", "log_rotate": 0}, "DBConnection": {"username": "", "retry_count": 0, "password": "", "type": "sqlite", "retry_interval": 0}, "Notification": {"default_template_new_event": "", "default_template_inspection": "", "default_template_pdf": ""}, "SMTP": {"username": "", "from": "", "envelope_from": "", "server": "", "security": "", "password": "", "port": 0}, "Server": {"software_version": "", "name": "", "DNS": ""}, "gmap_key": "", "Proxy": {"username": "", "use": false, "password": "", "port": 0, "server": ""}, "Services": {"use_geo_json": true, "ignore_nets": [], "new_eq_mag_cutoff": 0, "keep_eq_for": 0, "nighttime": 0, "check_new_int": 0, "night_eq_mag_cutoff": 0, "geo_json_web": "", "eq_req_products": [], "morning": 0, "archive_mag": 0, "geo_json_int": 0}, "timezone": 0}

    constructor(private confService: ConfigService,
                public timeService: TimeService) {}

    ngOnInit() {
        this.subscriptions.push(this.confService.configs.subscribe(configs => {
            this.configs = configs
        }));

        this.confService.getConfigs();
    }

    saveConfigs() {
        this.confService.saveConfigs(this.configs);
    }

    setTime() {

    }

    ngOnDestroy() {}
}
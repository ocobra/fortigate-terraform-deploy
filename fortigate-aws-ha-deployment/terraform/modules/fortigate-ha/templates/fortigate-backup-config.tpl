Content-Type: multipart/mixed; boundary="===============0086047718136476635=="
MIME-Version: 1.0

--===============0086047718136476635==
Content-Type: text/plain; charset="us-ascii"
MIME-Version: 1.0
Content-Transfer-Encoding: 7bit
Content-Disposition: attachment; filename="config"

config system global
    set hostname "${hostname}"
    set admin-password "${admin_password}"
end

config system sdn-connector
    edit "aws-sdn"
        set type aws
        set use-metadata-iam enable
        set region ${aws_region}
        set update-interval 60
        set status enable
    next
end

config system interface
    edit "port1"
        set vdom "root"
        set ip ${outside_ip} ${outside_netmask}
        set allowaccess ping https ssh http fgfm
        set type physical
        set description "outside"
        set alias "outside"
        set role wan
    next
    edit "port2"
        set vdom "root"
        set ip ${inside_ip} ${inside_netmask}
        set allowaccess ping https ssh http fgfm
        set type physical
        set description "inside"
        set alias "inside"
        set role lan
    next
    edit "port3"
        set vdom "root"
        set ip ${ha_ip} ${ha_netmask}
        set allowaccess ping https ssh http fgfm
        set type physical
        set description "ha"
        set alias "ha"
    next
    edit "port4"
        set vdom "root"
        set ip ${mgmt_ip} ${mgmt_netmask}
        set allowaccess ping https ssh http fgfm
        set type physical
        set description "mgmt"
        set alias "mgmt"
    next
end

config system ha
    set group-name "fortigate-ha-group"
    set mode a-p
    set hbdev "port3" 50
    set session-pickup enable
    set session-pickup-connectionless enable
    set ha-mgmt-status enable
    config ha-mgmt-interfaces
        edit 1
            set interface "port4"
            set gateway ${mgmt_gateway}
        next
    end
    set override disable
    set priority 100
    set monitor "port1" "port2"
    set password "${ha_password}"
end

config router static
    edit 1
        set gateway ${default_gateway}
        set device "port1"
        set comment "Default route to Internet via outside interface"
    next
    edit 2
        set dst 10.0.0.0 255.0.0.0
        set gateway ${inside_gateway}
        set device "port2"
        set comment "Route to 10.0.0.0/8 networks via Transit Gateway"
    next
    edit 3
        set dst 172.16.0.0 255.240.0.0
        set gateway ${inside_gateway}
        set device "port2"
        set comment "Route to 172.16.0.0/12 networks via Transit Gateway"
    next
    edit 4
        set dst 192.168.0.0 255.255.0.0
        set gateway ${inside_gateway}
        set device "port2"
        set comment "Route to 192.168.0.0/16 networks via Transit Gateway"
    next
end

config firewall policy
    edit 1
        set name "Outbound-Allow"
        set srcintf "port2"
        set dstintf "port1"
        set srcaddr "all"
        set dstaddr "all"
        set action accept
        set schedule "always"
        set service "ALL"
        set logtraffic all
        set nat enable
    next
    edit 2
        set name "Inbound-Deny"
        set srcintf "port1"
        set dstintf "port2"
        set srcaddr "all"
        set dstaddr "all"
        set action deny
        set schedule "always"
        set service "ALL"
        set logtraffic all
    next
end

config log setting
    set resolve-ip enable
    set resolve-port enable
    set log-user-in-upper enable
    set fwpolicy-implicit-log enable
    set local-in-allow enable
    set local-in-deny-unicast enable
    set local-in-deny-broadcast enable
    set local-out enable
end

config log syslogd setting
    set status enable
    set server "169.254.169.254"
    set mode udp
    set port 514
    set facility local7
    set source-ip ${mgmt_ip}
    set format default
end

--===============0086047718136476635==--
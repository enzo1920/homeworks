License:        BSD
Vendor:         Otus
Group:          PD01
URL:            http://otus.ru/lessons/3/
Source0:        otus-%{current_datetime}.tar.gz
BuildRoot:      %{_tmppath}/otus-%{current_datetime}
Name:           ip2w
Version:        0.0.1
Release:        1
BuildArch:      noarch
Requires(post): systemd
Requires(preun): systemd
Requires(postun): systemd
BuildRequires: systemd
Requires: python
Summary:  uWSGI ip2w server


%description

Daemon gets your IP, checks your location and gets weather forecast

Git version: %{git_version} (branch: %{git_branch})

%define __etcdir    /usr/local/etc/ip2w/
%define __logdir    /val/log/ip2w/
%define __bindir    /usr/local/ip2w/
%define __systemddir    /usr/lib/systemd/system/
%define __nginx /etc/nginx/

%prep

rm -rf %{buildroot}
%setup -n otus-%{current_datetime}


%install
[ "%{buildroot}" != "/" ] && rm -fr %{buildroot}
%{__mkdir} -p %{buildroot}%{__bindir}
%{__mkdir} -p %{buildroot}%{__etcdir}
%{__mkdir} -p %{buildroot}%{__logdir}
%{__mkdir} -p %{buildroot}%{__systemddir}
%{__mkdir} -p %{buildroot}%{__nginx}
%{__install} -pD -m 755 /home/homeworks/dz5/ip2w.py %{buildroot}%{__bindir}ip2w.py
%{__install} -pD -m 644 /home/homeworks/dz5/configs/ip2w.ini %{buildroot}%{__etcdir}ip2w.ini
%{__install} -pD -m 644 /home/homeworks/dz5/secret.json %{buildroot}%{__etcdir}secret.json
%{__install} -pD -m 644 /home/homeworks/dz5/service/ip2w.service %{buildroot}%{__systemddir}%{name}.service
%{__install} -pD -m 644 /home/homeworks/dz5/configs/nginx.conf %{buildroot}%{__nginx}%nginx.conf

%post
%systemd_post %{name}.service
systemctl daemon-reload
nginx -s quit
nginx -c nginx.conf

%preun
%systemd_preun %{name}.service

%postun
%systemd_postun %{name}.service
nginx -s quit
nginx

%clean
[ "%{buildroot}" != "/" ] && rm -fr %{buildroot}


%files
%{__etcdir}
%{__logdir}
%{__bindir}
%{__systemddir}
%{__nginx}

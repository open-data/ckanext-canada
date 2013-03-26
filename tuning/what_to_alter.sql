create index idx_harvest_object_guid on harvest_object(guid);
create index idx_harvest_object_pkg_id on harvest_object(package_id);
create index idx_harvest_object_id on harvest_object_extra(harvest_object_id);
create index idx_harvest_object_err on harvest_object_error(harvest_object_id);
create index idx_package_extend_pkg_id on package_extent(package_id);

create index idx_package_extra_revision_pkg_id on package_extra_revision(package_id);
create index idx_package_extra_revision on package_extra_revision(id);


--special
create index idx_revision_id on revision(id);
drop index idx_package_resource_pkg_id_resource_id;

create index idx_resource_name on resource(name);


create index idx_resource_group_pkg_id on resource_group(package_id);
create index idx_resource_group_revision_pkg_id on resource_group_revision(package_id);
create index idx_resource_group_revision_rev_id on resource_group_revision(revision_id);
create index idx_resource_group_revision on resource_group_revision(id);

create index idx_resource_revision on resource_revision(id);
create index idx_resource_revision_res_grp_id on resource_revision(resource_group_id);



drop INDEX idx_package_extra_current;
drop INDEX idx_package_extra_period;
drop INDEX idx_package_extra_period_package;
drop index idx_extra_id_pkg_id;

drop INDEX idx_package_tag_id ;

drop INDEX idx_package_tag_current ;
drop INDEX idx_package_tag_revision_pkg_id_tag_id ;
drop INDEX idx_period_package_tag ;

drop INDEX idx_resource_group_period ;
drop INDEX idx_resource_group_period_package ;
drop INDEX idx_resource_group_current ;

drop INDEX idx_resource_period;
drop INDEX idx_resource_current;
drop INDEX idx_resource_period_resource_group;


drop index idx_pkg_id;
drop index idx_pkg_name;
drop index idx_pkg_rev_id;
drop index idx_pkg_sid;
drop index idx_pkg_slname;
drop index idx_pkg_sname;
drop index idx_pkg_srev_id;
drop index idx_pkg_stitle;
drop index idx_pkg_suname;
drop index idx_pkg_title;
drop index idx_pkg_uname;

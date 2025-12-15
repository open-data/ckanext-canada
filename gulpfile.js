const { src, dest, watch, series } = require('gulp');
const rename = require('gulp-rename');
const sourcemaps = require('gulp-sourcemaps');
const sass = require('gulp-sass')(require('sass'));
const terser = require('gulp-terser');

function compileCustomSass(){
  return src('ckanext/canada/assets/custom/source/*.scss')
    .pipe(sourcemaps.init())
    .pipe(sass({style: 'compressed'}).on('error', sass.logError))
    .pipe(sourcemaps.write())
    .pipe(rename(function(_fileObj){
      _fileObj.extname = '.min.css';
    }))
    .pipe(dest('ckanext/canada/assets/custom/build'));
}

function compileDatatablesSass(){
  return src('ckanext/canada/assets/datatables/source/*.scss')
    .pipe(sourcemaps.init())
    .pipe(sass({style: 'compressed'}).on('error', sass.logError))
    .pipe(sourcemaps.write())
    .pipe(rename(function(_fileObj){
      _fileObj.extname = '.min.css';
    }))
    .pipe(dest('ckanext/canada/assets/datatables/build'));
}

function compileIMSass(){
  return src('ckanext/canada/assets/invitation-manager/vendor/*.css')
    .pipe(sourcemaps.init())
    .pipe(sass({style: 'compressed'}).on('error', sass.logError))
    .pipe(sourcemaps.write())
    .pipe(rename(function(_fileObj){
      _fileObj.extname = '.min.css';
    }))
    .pipe(dest('ckanext/canada/assets/invitation-manager/build'));
}

function watchSass(){
  watch('ckanext/canada/assets/custom/source/*.scss', compileCustomSass);
  watch('ckanext/canada/assets/datatables/source/*.scss', compileDatatablesSass);
  watch('ckanext/canada/assets/invitation-manager/vendor/*.css', compileIMSass);
}

function minifyCustomJS(){
  return src('ckanext/canada/assets/custom/source/*.js', {sourcemaps: true})
    .pipe(terser({'compress': true,
                  'mangle': true}))
    .pipe(rename(function(_fileObj){
      _fileObj.extname = '.min.js';
    }))
    .pipe(dest('ckanext/canada/assets/custom/build', {sourcemaps: true}));
}

function minifyDatatablesJS(){
  return src('ckanext/canada/assets/datatables/source/*.js', {sourcemaps: true})
    .pipe(terser({'compress': true,
                  'mangle': true}))
    .pipe(rename(function(_fileObj){
      _fileObj.extname = '.min.js';
    }))
    .pipe(dest('ckanext/canada/assets/datatables/build', {sourcemaps: true}));
}

function minifyIMJS(){
  return src('ckanext/canada/assets/invitation-manager/vendor/*.js', {sourcemaps: true})
    .pipe(terser({'compress': true,
                  'mangle': false}))
    .pipe(rename(function(_fileObj){
      _fileObj.extname = '.min.js';
    }))
    .pipe(dest('ckanext/canada/assets/invitation-manager/build', {sourcemaps: true}));
}

function watchJS(){
  watch('ckanext/canada/assets/custom/source/*.js', minifyCustomJS);
  watch('ckanext/canada/assets/datatables/source/*.js', minifyDatatablesJS)
  watch('ckanext/canada/assets/invitation-manager/vendor/*.js', minifyIMJS)
}

exports.build = series(compileCustomSass,
                       compileDatatablesSass,
                       compileIMSass,
                       minifyCustomJS,
                       minifyDatatablesJS,
                       minifyIMJS)
exports.watch = series(watchJS,
                       watchSass);
exports.buildCSS = series(compileCustomSass,
                          compileDatatablesSass,
                          compileIMSass);
exports.watchCSS = watchSass;
exports.buildJS = series(minifyCustomJS,
                         minifyDatatablesJS,
                         minifyIMJS);
exports.watchJS = watchJS;
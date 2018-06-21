"use strict";

const Path = require("path");
const Webpack = require("webpack");
const BundleTracker = require("webpack-bundle-tracker");
const ExtractTextPlugin = require("extract-text-webpack-plugin");
const ExtractSASS = new ExtractTextPlugin("../css/bundle-[hash].css");

module.exports = options => {
  const webpackConfig = {
    devtool: options.devtool,
    entry: {
      main: [
        `webpack-dev-server/client?http://localhost:${options.port}`,
        "webpack/hot/dev-server",
        "./src/scripts/index"
      ],
      style: './src/styles/main.sass',
      formResponseDetails: './src/scripts/form-response-details',
      formResponseList: './src/scripts/form-response-list'
    },
    output: {
      publicPath: "http://127.0.0.1:1339/",
      path: Path.join(__dirname, "static", "js"),
      filename: "bundle-[name]-[hash].min.js"
    },
    plugins: [
      new Webpack.DefinePlugin({
        "process.env": {
          NODE_ENV: JSON.stringify(
            options.isProduction ? "production" : "development"
          )
        }
      }),
      new BundleTracker({ filename: "./webpack-stats.json" })
    ],
    module: {
      loaders: [
        {
          test: /\.js$/,
          exclude: /(node_modules|bower_components)/,
          loader: "babel",
          query: {
            presets: ["es2015", "react"]
          }
        },
        {
          test: /\.(png|jpg|gif|svg)/,
          loader: "url-loader",
          options: {
            limit: 8192
          }
        },
        {
          test: /\.(woff|woff2|ttf|eot)/,
          loader: "file-loader"
        }
      ]
    }
  };

  if (options.isProduction) {
    webpackConfig.entry = ["./src/scripts/index"];
    webpackConfig.entry = {
      main: "./src/scripts/index",
      style : './src/styles/main.sass',
      formResponseDetails: './src/scripts/form-response-details',
      formResponseList: './src/scripts/form-response-list',
    },
    webpackConfig.output.publicPath = "/static/js/";

    webpackConfig.plugins.push(
      new Webpack.optimize.OccurenceOrderPlugin(),
      new Webpack.optimize.UglifyJsPlugin({
        compressor: {
          warnings: false
        }
      }),
      ExtractSASS
    );

    webpackConfig.module.loaders.push({
      test: /\.s[a|c]ss$/i,
      loader: ExtractSASS.extract(["css", "postcss", "sass"])
    });
  } else {
    webpackConfig.plugins.push(new Webpack.HotModuleReplacementPlugin());

    webpackConfig.module.loaders.push({
      test: /\.s[a|c]ss$/i,
      loaders: [
        'style',
        'css',
        'postcss',
        'sass',
      ]
    });

    webpackConfig.devServer = {
      hot: true,
      port: options.port,
      inline: true,
      progress: true,
      headers: { "Access-Control-Allow-Origin": "http://localhost:8000" } // django runserver
    };
  }

  return webpackConfig;
};

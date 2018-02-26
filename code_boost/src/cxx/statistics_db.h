/**
 * Class writing the statistics to the database.
 */

#ifndef CPP_PCAPREADER_STATISTICSDB_H
#define CPP_PCAPREADER_STATISTICSDB_H

#include <iostream>
#include <memory>
#include <string>
#include "statistics.h"
#include <SQLiteCpp/SQLiteCpp.h>

class statistics_db {
public:
    /*
     * Constructor: Creates new database / Opens existing database
     */
    statistics_db(std::string database_path);

    /*
     * Database version: Increment number on every change in the C++ code!
     */
    static const int DB_VERSION = 1;

    /*
     * Methods for writing values into database
     */
    void writeStatisticsIP(std::unordered_map<std::string, entry_ipStat> ipStatistics);

    void writeStatisticsTTL(std::unordered_map<ipAddress_ttl, int> ttlDistribution);

    void writeStatisticsMSS(std::unordered_map<ipAddress_mss, int> mssDistribution);

    void writeStatisticsToS(std::unordered_map<ipAddress_tos, int> tosDistribution);

    void writeStatisticsWin(std::unordered_map<ipAddress_win, int> winDistribution);

    void writeStatisticsProtocols(std::unordered_map<ipAddress_protocol, int> protocolDistribution);

    void writeStatisticsPorts(std::unordered_map<ipAddress_inOut_port, int> portsStatistics);

    void writeStatisticsIpMac(std::unordered_map<std::string, std::string> IpMacStatistics);

    void writeStatisticsFile(int packetCount, float captureDuration, std::string timestampFirstPkt,
                             std::string timestampLastPkt, float avgPacketRate, float avgPacketSize,
                             float avgPacketsSentPerHost, float avgBandwidthIn, float avgBandwidthOut);

    void writeStatisticsConv(std::unordered_map<conv, entry_convStat> convStatistics);

    void writeStatisticsInterval(std::unordered_map<std::string, entry_intervalStat> intervalStatistics);

    void writeDbVersion();

private:
    // Pointer to the SQLite database
    std::unique_ptr<SQLite::Database> db;


};


#endif //CPP_PCAPREADER_STATISTICSDB_H

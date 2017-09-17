/**
 * Class for processing PCAPs to collect statistical data.
 */

#ifndef CPP_PCAPREADER_MAIN_H
#define CPP_PCAPREADER_MAIN_H

// Aidmar
#include <iomanip>

#include <tins/tins.h>
#include <iostream>
#include <time.h>
#include <stdio.h>
#include <sys/stat.h>
#include <unordered_map>
#include "statistics.h"

using namespace Tins;

class pcap_processor {

public:
    /*
    * Class constructor
    */
    pcap_processor(std::string path, std::string tests);

    /*
     * Attributes
     */
    statistics stats;
    std::string filePath;

    /*
     * Methods
     */
    inline bool file_exists(const std::string &filePath);

    void process_packets(const Packet &pkt);

    long double get_timestamp_mu_sec(const int after_packet_number);

    std::string merge_pcaps(const std::string pcap_path);

    void collect_statistics();

    void write_to_database(std::string database_path);
};


#endif //CPP_PCAPREADER_MAIN_H

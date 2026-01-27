#ifndef TEXT_CLASSIFIER_H
#define TEXT_CLASSIFIER_H

#include <string>
#include <vector>
#include <map>
#include <set>
#include <cmath>
#include <iostream>
#include <fstream>
#include <sstream>
#include <algorithm>

class TextClassifier {
private:
    struct IntentData {
        std::map<std::string, double> tfidf_vector;
        double magnitude;
    };

    std::map<std::string, IntentData> intents;
    std::map<std::string, double> global_idf;
    std::set<std::string> vocabulary;
    
    // Helper to tokenize and normalize
    std::vector<std::string> tokenize(const std::string& text) {
        std::vector<std::string> tokens;
        std::string lower_text = text;
        std::transform(lower_text.begin(), lower_text.end(), lower_text.begin(), ::tolower);
        
        std::stringstream ss(lower_text);
        std::string word;
        while (ss >> word) {
            // Remove punctuation
            word.erase(std::remove_if(word.begin(), word.end(), ::ispunct), word.end());
            if (!word.empty()) {
                tokens.push_back(word);
            }
        }
        return tokens;
    }

public:
    TextClassifier() {}

    // Load data and "train" the model
    bool train(const std::string& filepath) {
        std::ifstream file(filepath);
        if (!file.is_open()) return false;

        std::string line;
        std::map<std::string, std::vector<std::string>> raw_data;
        int total_docs = 0;

        // 1. Read and tokenize
        while (std::getline(file, line)) {
            size_t delim = line.find(':');
            if (delim == std::string::npos) continue;

            std::string label = line.substr(0, delim);
            std::string phrase = line.substr(delim + 1);
            
            // Trim label
            label.erase(0, label.find_first_not_of(" 	"));
            label.erase(label.find_last_not_of(" 	") + 1);

            std::vector<std::string> tokens = tokenize(phrase);
            for (const auto& w : tokens) {
                raw_data[label].push_back(w);
                vocabulary.insert(w);
            }
            total_docs++; // We treat each line as a doc for IDF? Or each class?
            // Actually for classification, let's treat each Class as one large document for TF.
            // And use line-count for IDF calculation across the whole set?
            // Let's stick to: "Word appears in N documents" where document = line.
        }

        // 2. Calculate IDF
        // global_idf[word] = log(total_lines / (1 + count_of_lines_containing_word))
        file.clear();
        file.seekg(0);
        std::map<std::string, int> doc_freq;
        
        while (std::getline(file, line)) {
             size_t delim = line.find(':');
             if (delim == std::string::npos) continue;
             std::string phrase = line.substr(delim + 1);
             std::vector<std::string> tokens = tokenize(phrase);
             std::set<std::string> unique_tokens(tokens.begin(), tokens.end());
             for(const auto& w : unique_tokens) {
                 doc_freq[w]++;
             }
        }

        for (const auto& w : vocabulary) {
            global_idf[w] = std::log((double)total_docs / (1.0 + doc_freq[w]));
        }

        // 3. Build Centroids (TF-IDF vectors for each intent)
        for (const auto& entry : raw_data) {
            const std::string& label = entry.first;
            const std::vector<std::string>& words = entry.second;
            
            std::map<std::string, int> tf;
            for (const auto& w : words) tf[w]++;

            IntentData data;
            data.magnitude = 0.0;

            for (const auto& w : words) {
                // TF = count in this class / total words in this class (Normalized TF)
                // OR just raw count. Let's use Raw Count * IDF for simplicity in centroid.
                double val = (double)tf[w] * global_idf[w];
                data.tfidf_vector[w] = val; // Store just non-zero
            }

            // Calculate magnitude for Cosine Sim
            double sum_sq = 0;
            for (auto const& [w, val] : data.tfidf_vector) { // Loop over unique words
                 // Note: we iterate raw_data words above, so we might overwrite. 
                 // Better to iterate the map we just built.
                 sum_sq += val * val;
            }
            data.magnitude = std::sqrt(sum_sq);
            intents[label] = data;
        }
        
        std::cout << "Training complete. Vocabulary size: " << vocabulary.size() << ", Intents: " << intents.size() << std::endl;
        return true;
    }

    std::string predict(const std::string& query) {
        std::vector<std::string> tokens = tokenize(query);
        std::map<std::string, double> query_vec;
        
        // Build query vector
        double query_mag = 0.0;
        for (const auto& w : tokens) {
            if (vocabulary.find(w) != vocabulary.end()) {
                double val = 1.0 * global_idf[w]; // TF=1 for query
                query_vec[w] += val;
            }
        }
        
        for (const auto& pair : query_vec) {
            query_mag += pair.second * pair.second;
        }
        query_mag = std::sqrt(query_mag);

        if (query_mag == 0) return "unknown";

        // Find closest intent (Cosine Similarity)
        std::string best_intent = "unknown";
        double max_sim = 0.0;

        for (const auto& entry : intents) {
            const std::string& label = entry.first;
            const IntentData& data = entry.second;

            double dot = 0.0;
            for (const auto& q_pair : query_vec) {
                const std::string& word = q_pair.first;
                double q_val = q_pair.second;
                
                if (data.tfidf_vector.count(word)) {
                    dot += q_val * data.tfidf_vector.at(word);
                }
            }

            if (data.magnitude > 0) {
                double sim = dot / (query_mag * data.magnitude);
                if (sim > max_sim) {
                    max_sim = sim;
                    best_intent = label;
                }
            }
        }

        // Threshold
        if (max_sim < 0.2) return "unknown"; // Low confidence
        return best_intent;
    }
};

#endif

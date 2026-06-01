package com.literatureassistant.mapper;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.literatureassistant.dto.response.PaperDetailResponse;
import com.literatureassistant.dto.response.PaperResponse;
import com.literatureassistant.entity.Paper;
import org.mapstruct.Mapper;
import org.mapstruct.Mapping;
import org.mapstruct.Named;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.List;

@Mapper(componentModel = "spring", uses = {PaperMapper.JsonStringListHelper.class})
public interface PaperMapper {

    @Mapping(target = "authors", source = "authors", qualifiedByName = "jsonToList")
    @Mapping(target = "keywords", source = "keywords", qualifiedByName = "jsonToList")
    PaperResponse toResponse(Paper paper);

    @Mapping(target = "authors", source = "authors", qualifiedByName = "jsonToList")
    @Mapping(target = "keywords", source = "keywords", qualifiedByName = "jsonToList")
    PaperDetailResponse toDetailResponse(Paper paper);

    @Component
    class JsonStringListHelper {

        private static final Logger log = LoggerFactory.getLogger(JsonStringListHelper.class);

        private final ObjectMapper objectMapper;

        public JsonStringListHelper(ObjectMapper objectMapper) {
            this.objectMapper = objectMapper;
        }

        @Named("jsonToList")
        public List<String> jsonToList(String json) {
            if (json == null || json.isBlank()) {
                return List.of();
            }
            try {
                return objectMapper.readValue(json, new TypeReference<List<String>>() {
                });
            } catch (JsonProcessingException e) {
                log.warn("Failed to parse JSON field: {}", json);
                return List.of();
            }
        }

        @Named("listToJson")
        public String listToJson(List<String> list) {
            if (list == null || list.isEmpty()) {
                return "[]";
            }
            try {
                return objectMapper.writeValueAsString(list);
            } catch (JsonProcessingException e) {
                log.warn("Failed to serialize list to JSON: {}", list);
                return "[]";
            }
        }
    }
}

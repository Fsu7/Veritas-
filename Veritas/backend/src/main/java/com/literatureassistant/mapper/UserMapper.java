package com.literatureassistant.mapper;

import com.literatureassistant.dto.response.ProfileResponse;
import com.literatureassistant.dto.response.UserResponse;
import com.literatureassistant.entity.User;
import com.literatureassistant.entity.UserProfile;
import org.mapstruct.Mapper;
import org.mapstruct.Mapping;

@Mapper(componentModel = "spring")
public interface UserMapper {

    @Mapping(target = "hasProfile", source = "hasProfile")
    @Mapping(target = "createdAt", source = "user.createdAt")
    UserResponse toUserResponse(User user, boolean hasProfile);

    @Mapping(target = "userId", source = "profile.userId")
    @Mapping(target = "educationLevel", expression = "java(profile.getEducationLevel().getDbValue())")
    @Mapping(target = "knowledgeLevel", expression = "java(profile.getKnowledgeLevel().getDbValue())")
    @Mapping(target = "preferredStyle", expression = "java(profile.getPreferredStyle().getDbValue())")
    @Mapping(target = "updatedAt", source = "profile.updatedAt")
    ProfileResponse toProfileResponse(UserProfile profile);
}
